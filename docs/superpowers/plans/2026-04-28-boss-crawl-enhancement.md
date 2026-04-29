# Boss Zhipin Crawl Enhancement — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the Boss Zhipin crawling pipeline with cron scheduling, multi-config support, smarter deduplication, and job description scraping.

**Architecture:** The existing job crawl pipeline (`boss.py` → `job_crawl.py` → `main.py`) already supports API-based cron scheduling via APScheduler. We extend the cron trigger, refine the dedup logic to use a "grace period" window instead of immediate deactivation, and add a detail-page scraper that reuses the raw WebSocket CDP + curl_cffi pattern proven in `boss.py`.

**Tech Stack:** Python 3.11+ · FastAPI · APScheduler 3.x · SQLAlchemy async · curl_cffi · websockets · React + Ant Design

---

## File Structure

| File | Responsibility |
|------|---------------|
| `backend/app/models/job.py` | Add `consecutive_miss_count`, `last_active_at` to Job; `deactivation_threshold` to JobSearchConfig |
| `backend/app/services/scheduler_job.py` | New: `trigger_job_crawl()` — module-level APScheduler job trigger (shared by main.py and config endpoint) |
| `backend/app/services/job_crawl.py` | Dedup grace period + job detail crawler + export `trigger_job_crawl` via scheduler_job import |
| `backend/app/schemas/user.py` | Add `job_crawl_cron` to UserConfigUpdate and UserConfigResponse |
| `backend/app/routers/config.py` | Add GET /config/job-crawl-cron, PUT /config/job-crawl-cron, `_rebuild_job_crawl_scheduler_job()` |
| `backend/app/main.py:88-113` | Import `trigger_job_crawl` from scheduler_job.py (was local `_trigger_crawl_jobs`) |
| `backend/alembic/versions/006_add_job_grace_fields.py` | Migration for Job grace period columns |
| `backend/alembic/versions/007_add_config_deactivation_threshold.py` | Migration for JobSearchConfig.deactivation_threshold |
| `backend/app/platforms/boss_detail.py` | New: detail page scraper via raw CDP + curl_cffi |
| `frontend/src/api/config.ts` | New: API call for `/config/job-crawl-cron` (separate from jobs.ts) |
| `frontend/src/pages/JobsPage.tsx` | Show cron status / next run time |
| `frontend/src/components/JobConfigForm.tsx` | Expose cron field (optional, for general settings page) |

Note: JobConfigForm.tsx is per-config, NOT the right place for global cron settings. Put the cron field in a general Settings page or separate CronSettings component, NOT in the per-config form.

---

### Task 1: Cron scheduler — verify, expose, and configure

**Current state:** `main.py` already registers `job_crawl_cron_job` with APScheduler using `user.job_crawl_cron` defaulting to `"0 9 * * *"`. The cron runs `crawl_all_job_searches(source="cron")` on schedule. No frontend/config API to change it.

**Files:**
- Modify: `backend/app/schemas/user.py`
- Modify: `backend/app/routers/config.py:1-50`
- Modify: `frontend/src/components/JobConfigForm.tsx`

- [ ] **Step 1: Add `job_crawl_cron` to User schema response**

```python
# backend/app/schemas/user.py — add to UserConfigUpdate
class UserConfigUpdate(BaseModel):
    # ... existing fields ...
    job_crawl_cron: str | None = Field(default=None, description="Job crawl cron expression")

    @field_validator("job_crawl_cron")
    @classmethod
    def validate_job_cron(cls, v: str | None) -> str | None:
        if v is None or v.strip() == "":
            return None
        parts = v.strip().split()
        if len(parts) != 5:
            raise ValueError("Job cron 必须是 5 段格式（分 时 日 月 周）")
        for i, seg in enumerate(parts):
            if not _CRON_SEGMENT_RE.match(seg):
                raise ValueError(f"Cron 第{i+1}段 '{seg}' 格式不正确")
        return v

# backend/app/schemas/user.py — add to UserConfigResponse
class UserConfigResponse(BaseModel):
    # ... existing fields ...
    job_crawl_cron: str | None = None
```

Note: `UserConfigResponse` and `UserConfigUpdate` are the existing schema names — do NOT use `UserResponse` or `UserUpdate`.

- [ ] **Step 2: Add `job_crawl_cron` reschedule to PATCH /config**

> Instead of a separate PUT endpoint, extend PATCH /config to also handle
> `job_crawl_cron` changes. This avoids duplicate code with the existing
> `crawl_cron` reschedule logic.

Modify `backend/app/routers/config.py` and create `backend/app/services/scheduler_job.py`:

0. Create `backend/app/services/scheduler_job.py` with the module-level trigger:

```python
# backend/app/services/scheduler_job.py — NEW FILE
"""Module-level APScheduler job triggers (avoids circular imports)."""

import asyncio
import logging

logger = logging.getLogger(__name__)


async def trigger_job_crawl() -> None:
    """APScheduler job callback: crawl all active job searches.

    Defined at module level so main.py and config.py can both import it
    without circular dependencies. APScheduler holds a reference to this
    function — it must be importable by name, not a local function.
    """
    from app.services.job_crawl import crawl_all_job_searches
    logger.info("Job crawl cron triggered")
    asyncio.create_task(crawl_all_job_searches(source="cron"))
```

1. Add `_rebuild_job_crawl_scheduler_job(cron_expr, timezone_str)` in config.py (uses `scheduler_job.trigger_job_crawl`):

```python
def _rebuild_job_crawl_scheduler_job(cron_expr: str, timezone_str: str) -> None:
    """Hot-reload the job_crawl_cron APScheduler job. Used by PATCH /config."""
    from app.services.scheduler_job import trigger_job_crawl
    scheduler = _get_scheduler()
    if scheduler is None:
        logger.info("Scheduler not initialized, skipping job_crawl job rebuild")
        return
    job_id = "job_crawl_cron_job"
    try:
        existing = scheduler.get_job(job_id)
        if existing:
            scheduler.remove_job(job_id)
            logger.info("Removed existing job_crawl_cron job")
        if cron_expr:
            import zoneinfo
            from apscheduler.triggers.cron import CronTrigger
            tz = zoneinfo.ZoneInfo(timezone_str)
            scheduler.add_job(
                trigger_job_crawl,
                trigger=CronTrigger.from_crontab(cron_expr, timezone=tz),
                id=job_id,
                name="Crawl all active job searches",
                replace_existing=True,
                max_instances=1,
            )
            logger.info("Registered job_crawl_cron_job with schedule '%s' (tz=%s)", cron_expr, timezone_str)
    except Exception:
        logger.exception("Failed to rebuild job_crawl_cron job")
        raise
```

2. Add GET /config/job-crawl-cron for explicit cron readout:

```python
@router.get("/job-crawl-cron")
async def get_job_crawl_cron(db: AsyncSession = Depends(get_db)):
    """Get current job crawl cron expression."""
    result = await db.execute(select(User).where(User.id == 1))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "job_crawl_cron": user.job_crawl_cron,
        "default": "0 9 * * *",
        "timezone": user.crawl_timezone or "Asia/Shanghai",
    }
```

3. Add a dedicated PUT endpoint for the frontend cron field (POST /config/job-crawl-cron) that mirrors the existing `_rebuild_job_crawl_scheduler_job` pattern:

```python
from pydantic import BaseModel

class JobCrawlCronUpdate(BaseModel):
    job_crawl_cron: str | None = None

@router.put("/job-crawl-cron", response_model=JobCrawlCronUpdate)
async def update_job_crawl_cron(
    data: JobCrawlCronUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update job crawl cron expression and reschedule the APScheduler job."""
    from app.services.scheduler_job import trigger_job_crawl
    result = await db.execute(select(User).where(User.id == 1))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    cron_expr = data.job_crawl_cron or ""
    if cron_expr.strip():
        from apscheduler.triggers.cron import CronTrigger
        try:
            import zoneinfo
            tz = zoneinfo.ZoneInfo(user.crawl_timezone or "Asia/Shanghai")
            CronTrigger.from_crontab(cron_expr, timezone=tz)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid cron expression")

    user.job_crawl_cron = cron_expr.strip() or None
    await db.commit()

    # Reschedule
    _rebuild_job_crawl_scheduler_job(
        user.job_crawl_cron or "",
        user.crawl_timezone or "Asia/Shanghai",
    )

    return JobCrawlCronUpdate(job_crawl_cron=user.job_crawl_cron)
```

Note: `trigger_job_crawl()` is defined in `backend/app/services/scheduler_job.py` — shared by main.py and config endpoint.
```

- [ ] **Step 3: Expose cron setting in UI**

The cron field is a global setting, not per-config. Add it to a Settings section or a dedicated CronSettings component. Create `frontend/src/api/config.ts`:

```typescript
// frontend/src/api/config.ts
import api from './client'

export const configApi = {
  getJobCrawlCron: () =>
    api.get<{ job_crawl_cron: string | null; default: string; timezone: string }>(
      '/config/job-crawl-cron',
    ),
  updateJobCrawlCron: (job_crawl_cron: string | null) =>
    api.put<{ job_crawl_cron: string | null }>('/config/job-crawl-cron', {
      job_crawl_cron,
    }),
}
```

Then add a CronSettings component (not in JobConfigForm) with an Input field for the cron expression and save button calling `configApi.updateJobCrawlCron()`.

- [ ] **Step 4: Add automated test for cron endpoint**

```python
# backend/tests/test_api.py — add

@pytest.mark.asyncio
async def test_get_job_crawl_cron_returns_default():
    """GET /config/job-crawl-cron returns job_crawl_cron from DB or default."""
    from app.database import get_db
    from app.models.user import User

    mock_user = MagicMock(spec=User)
    mock_user.job_crawl_cron = "0 9 * * *"
    mock_user.crawl_timezone = "Asia/Shanghai"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user

    mock_db = MagicMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch("app.routers.config.get_db", return_value=mock_db):
        from httpx import ASGITransport, AsyncClient
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/config/job-crawl-cron")
        assert resp.status_code == 200
        assert "job_crawl_cron" in resp.json()

Run: `cd backend && pytest tests/test_api.py::test_get_job_crawl_cron_returns_default -v`

- [ ] **Step 5: Test cron endpoint (manual)**

Start backend, call `GET /config/job-crawl-cron`, verify response. Then `PUT /config/job-crawl-cron` with `{"job_crawl_cron": "30 8 * * *"}` and verify `/scheduler/status` shows the new schedule.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/user.py backend/app/routers/config.py frontend/src/components/JobConfigForm.tsx
git commit -m "feat: expose job_crawl_cron config via API and frontend"
```

---

### Task 2: Frontend — verify full end-to-end flow

**Current state:** JobConfigForm, JobConfigList, JobList, JobsPage already exist. Need to verify the complete user journey works end-to-end with real data.

**Files:**
- No code changes — verification only
- Test: manual walkthrough

- [ ] **Step 1: Start backend and frontend**

Run: `cd backend && uvicorn app.main:app` and `cd frontend && npm run dev`

- [ ] **Step 2: Create a new JobSearchConfig via UI**

Navigate to `http://localhost:3000/jobs` → click "添加配置" → fill form with:
- Name: `深圳 Java`
- URL: `https://www.zhipin.com/web/geek/jobs?query=java&city=101280600`

Verify config appears in list.

- [ ] **Step 3: Trigger manual crawl**

Click "立即抓取" button on the config row. Wait for completion.

- [ ] **Step 4: Verify jobs appear**

Navigate to Jobs list. Verify new jobs appear with correct title, company, salary, location.

- [ ] **Step 5: Verify cron status**

Navigate to `/scheduler/status`. Verify cron is registered and shows next run time.

- [ ] **Step 6: Commit (documentation only)**

No code changes — record verification status in plan.

---

### Task 3: Multi-keyword / multi-city support

**Current state:** `crawl_all_job_searches()` already iterates all active `JobSearchConfig` rows and crawls each. Multiple configs work by design — we just need to demonstrate and fix any bugs.

**Files:**
- Modify: `backend/app/services/job_crawl.py:216-246` — `crawl_all_job_searches`

- [ ] **Step 1: Add sequential delay between configs**

Each config's crawl consumes a CDP new-tab refresh (~5s), so back-to-back crawls without a gap risk rate-limiting. Add a delay between configs. The `random` import is already needed for page-level delays in `boss.py`.

```python
# backend/app/services/job_crawl.py — inside crawl_all_job_searches()

async def crawl_all_job_searches(source: str = "manual") -> dict:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(JobSearchConfig).where(JobSearchConfig.active)
        )
        configs = list(result.scalars().all())

    if not configs:
        return {"status": "completed", "total": 0, "success": 0, "errors": 0}

    total = len(configs)
    success_count = 0
    error_count = 0
    details = []

    for i, config in enumerate(configs):
        result = await crawl_single_config(config.id)
        details.append({"config_id": config.id, **result})
        if result.get("status") == "success":
            success_count += 1
        else:
            error_count += 1

        # Space out configs to avoid CDP exhaustion (new-tab refresh is ~5s)
        if i < len(configs) - 1:
            delay = random.uniform(3, 6)
            logger.debug("Waiting %.1fs before next config", delay)
            await asyncio.sleep(delay)

    return {
        "status": "completed",
        "total": total,
        "success": success_count,
        "errors": error_count,
        "details": details,
    }
```

- [ ] **Step 2: Add a second config via API for testing**

```bash
curl -X POST http://127.0.0.1:8000/jobs/configs \
  -H "Content-Type: application/json" \
  -d '{"name":"深圳 Java","url":"https://www.zhipin.com/web/geek/jobs?query=java&city=101280600","user_id":1}'
```

- [ ] **Step 3: Run `crawl_all_job_searches` and verify both succeed**

```bash
curl -X POST http://127.0.0.1:8000/jobs/crawl-now
```

Verify both configs produce jobs without rate-limiting errors.

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/job_crawl.py
git commit -m "feat: add inter-config delay in crawl_all_job_searches"
```

---

### Task 4: Deduplication — grace period instead of immediate deactivation

**Current state:** `process_job_results()` immediately sets `is_active=False` for any previously-seen job not present in the current crawl. Each crawl pulls a different subset of the search results (Boss pagination isn't perfectly deterministic), so jobs ping-pong between active/inactive.

**Design decision:** Add a "grace period" — a job is only deactivated after it's been absent for `N` consecutive crawls. This is configurable per `JobSearchConfig`.

**Files:**
- Modify: `backend/app/models/job.py` — add `consecutive_miss_count`, `last_active_at`
- Create: `backend/alembic/versions/006_add_job_grace_fields.py`
- Modify: `backend/app/services/job_crawl.py` — grace-period dedup logic
- Modify: `backend/app/models/job.py:JobSearchConfig` — add `deactivation_threshold` column
- Create: `backend/alembic/versions/007_add_config_deactivation_threshold.py`

- [ ] **Step 4a: Add columns to Job model**

```python
# backend/app/models/job.py — add to Job class

consecutive_miss_count = Column(Integer, nullable=False, default=0)
# Number of consecutive crawls where this job was NOT seen.
# Reset to 0 when the job IS seen. Deactivated when >= threshold.

last_active_at = Column(
    DateTime(timezone=True), nullable=True,
    default=lambda: datetime.now(UTC),
)
# Timestamp when this job was last seen in a crawl.
```

- [ ] **Step 4b: Add deactivation_threshold to JobSearchConfig**

```python
# backend/app/models/job.py — add to JobSearchConfig class

deactivation_threshold = Column(
    Integer, nullable=False, default=3,
    comment="Consecutive crawl misses before marking a job inactive",
)
```

- [ ] **Step 4c: Create migrations**

```bash
cd backend && alembic revision --autogenerate -m "add job grace fields and deactivation threshold"
alembic upgrade head
```

- [ ] **Step 4d: Replace immediate deactivation with grace-period logic**

```python
# backend/app/services/job_crawl.py — replace lines 87-91

# Old (immediate):
# for job in all_active_jobs:
#     if job.job_id not in seen_job_ids:
#         job.is_active = False

# New (grace period):
threshold = config.deactivation_threshold or 3

for job in all_active_jobs:
    if job.job_id in seen_job_ids:
        # Job is still present — reset counter
        job.consecutive_miss_count = 0
        job.last_active_at = datetime.now(UTC)
    else:
        # Job not seen this crawl — increment miss counter
        job.consecutive_miss_count += 1
        if job.consecutive_miss_count >= threshold:
            job.is_active = False
            job.last_updated_at = datetime.now(UTC)
            deactivated_count += 1
```

- [ ] **Step 4e: Add regression test for current dedup behavior**

Before changing the dedup logic, write a test that captures the current (immediate deactivation) behavior so we have a baseline. Create `tests/test_job_crawl.py`:

```python
# backend/tests/test_job_crawl.py

import pytest
from unittest.mock import AsyncMock, patch
from datetime import UTC, datetime

from app.services.job_crawl import process_job_results


@pytest.mark.asyncio
async def test_process_job_results_deactivates_absent_jobs_immediately():
    """REGRESSION TEST: Job not in current crawl should be deactivated immediately."""
    with patch("app.services.job_crawl.AsyncSessionLocal") as mock_session_cls:
        # ... mock config with default deactivation_threshold ...
        # Crawl 1: job "abc" is present → active
        result1 = await process_job_results(config_id=1, jobs=[{"job_id": "abc", "title": "Dev"}], total_scraped=1)
        assert result1["new_count"] == 1

        # Crawl 2: job "abc" is absent → should be deactivated (current behavior)
        result2 = await process_job_results(config_id=1, jobs=[], total_scraped=0)
        assert result2["deactivated_count"] == 1
```

Run: `cd backend && pytest tests/test_job_crawl.py::test_process_job_results_deactivates_absent_jobs_immediately -v`
Expected: PASS (captures current behavior)

- [ ] **Step 4f: Run regression tests**

```bash
cd backend && pytest tests/test_job_crawl.py -v
```

- [ ] **Step 4g: Add test for grace-period behavior**

```python
# backend/tests/test_job_crawl.py — add test

@pytest.mark.asyncio
async def test_job_deactivation_grace_period():
    """Job should survive N-1 consecutive misses before deactivation."""
    from app.services.job_crawl import process_job_results

    # Insert a config with threshold=2
    async with AsyncSessionLocal() as db:
        config = JobSearchConfig(
            id=999, user_id=1, name="test", url="http://test",
            deactivation_threshold=2,
        )
        db.add(config)
        await db.commit()

    # Crawl 1: job appears
    result1 = await process_job_results(999, [{"job_id": "abc123", "title": "Test"}], 1)
    assert result1["new_count"] == 1
    assert result1["deactivated_count"] == 0

    # Crawl 2: job absent — miss_count=1, still active
    result2 = await process_job_results(999, [], 0)
    async with AsyncSessionLocal() as db:
        job = await db.get(Job, "abc123")
        assert job.is_active
        assert job.consecutive_miss_count == 1

    # Crawl 3: job absent again — miss_count=2 >= threshold, deactivated
    result3 = await process_job_results(999, [], 0)
    async with AsyncSessionLocal() as db:
        job = await db.get(Job, "abc123")
        assert not job.is_active
```

- [ ] **Step 4h: Run full test suite**

```bash
cd backend && pytest tests/ -q --ignore=tests/test_integration_realdb.py --ignore=tests/screenshots
```

- [ ] **Step 4i: Commit**

```bash
git add backend/app/models/job.py backend/app/services/job_crawl.py \
        backend/alembic/versions/006_*.py backend/alembic/versions/007_*.py \
        backend/tests/test_job_crawl.py
git commit -m "feat: add grace-period deduplication for job deactivation"
```

---

### Task 5: Job description crawling (detail pages)

**Current state:** Only list-page fields are captured (title, company, salary, etc.). The `description` column in `Job` model is unused.

**Design decision:** Use the same raw WebSocket CDP + curl_cffi pattern that works for the list API. The job detail API endpoint is likely `wapi/zpgeek/job/detail.json?securityId=XXX`. We test this hypothesis first, then build a light adapter.

**Files:**
- Create: `backend/app/platforms/boss_detail.py`
- Modify: `backend/app/services/job_crawl.py`
- Test: `backend/tests/test_boss_detail.py`

- [ ] **Step 1: Discover the detail API endpoint** ⚠️ BLOCKER: This MUST be run and validated before Step 2.

> ⚠️ **Important:** The code samples in Steps 2-6 are based on the assumption that
> `wapi/zpgeek/job/detail.json?securityId={job_id}` is the correct endpoint. This
> is NOT verified. Step 1 must succeed (return `code=0` with structured job detail
> data) before proceeding. If Step 1 fails, update the plan with the actual
> working endpoint before implementing Steps 2-6.

Write a quick diagnostic script to test known Boss detail API patterns:

```python
# Run as inline test — not committed
import asyncio, json, http.client, websockets
from curl_cffi.requests import Session as CffiSession

async def test_detail_api():
    # Get CDP cookies (reuse existing boss.py pattern)
    # ... cookie extraction ...

    job_id = "encryptJobId_from_list_crawl"  # from a known job
    session = CffiSession()
    session.cookies.update(cookies)

    # Try known detail API patterns
    patterns = [
        f"/wapi/zpgeek/job/detail.json?securityId={job_id}",
        f"/wapi/zpgeek/job/detail.json?encryptJobId={job_id}",
        f"/wapi/zpgeek/job/detail/{job_id}",
    ]
    for p in patterns:
        r = session.get(f"https://www.zhipin.com{p}", impersonate="chrome124",
                        headers={"Referer": "https://www.zhipin.com/"})
        print(f"{p}: status={r.status_code} code={r.json().get('code')}")
        if r.json().get("code") == 0:
            print(json.dumps(r.json(), indent=2, ensure_ascii=False)[:1000])
            return r.json()
```

Run this, capture the actual API endpoint and response format.

- [ ] **Step 2: Implement `BossDetailAdapter`**

Based on the discovered endpoint, create the detail adapter:

```python
# backend/app/platforms/boss_detail.py

"""Boss Zhipin job detail page scraper.

Uses the same raw CDP + curl_cffi pattern as boss.py.
Extracts full job description text, company info, and requirements
from the detail API (wapi/zpgeek/job/detail.json).
"""

import asyncio
import logging
from typing import Any
from curl_cffi.requests import Session as CffiSession
from app.platforms.boss import BossZhipinAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://www.zhipin.com"


class BossDetailAdapter:
    """Scrape job description from Boss detail API."""

    def __init__(self):
        self._boss_adapter = BossZhipinAdapter()

    async def fetch_description(self, job_id: str, encrypt_id: str = "") -> dict[str, Any]:
        """Fetch job detail. Returns {"description": str, ...} or {"error": str}."""
        try:
            session = CffiSession()

            # Reuse boss.py's cookie acquisition (CDP → disk → new-tab cascade)
            session.cookies.update(
                await self._boss_adapter._get_cookies_via_raw_cdp()
                or self._boss_adapter._load_cookies()
            )

            detail_id = encrypt_id or job_id
            api_url = (
                f"{BASE_URL}/wapi/zpgeek/job/detail.json"
                f"?securityId={job_id}"
            )

            resp = session.get(
                api_url,
                impersonate="chrome124",
                headers={"Referer": f"{BASE_URL}/job_detail/{detail_id}.html"},
            )

            if resp.status_code != 200:
                return {"error": f"HTTP {resp.status_code}"}

            data = resp.json()
            if data.get("code") != 0:
                return {"error": f"API code={data.get('code')}"}

            zp_data = data.get("zpData", {})
            job_info = zp_data.get("jobInfo", {}) or zp_data.get("jobDetail", {})

            return {
                "description": job_info.get("jobDescription", "")
                               or job_info.get("jobContent", "")
                               or job_info.get("detail", ""),
                "requirements": job_info.get("jobRequire", ""),
                "address": job_info.get("address", ""),
                "company_info": zp_data.get("companyInfo", {}).get("detail", ""),
            }

        except Exception as e:
            logger.warning("Detail fetch failed for job %s: %s", job_id, e)
            return {"error": str(e)}
```

- [ ] **Step 3: Integrate detail fetching into the crawl pipeline**

Add a post-processing step in `crawl_single_config` (or a new function) that fetches descriptions for NEW jobs only:

```python
# backend/app/services/job_crawl.py — add after process_job_results()

async def backfill_descriptions(config_id: int, limit: int = 30) -> int:
    """Fetch descriptions for jobs that don't have one yet."""
    from app.platforms.boss_detail import BossDetailAdapter

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Job).where(
                Job.search_config_id == config_id,
                Job.description.is_(None),
                Job.is_active,
            ).limit(limit)
        )
        jobs = list(result.scalars().all())

    if not jobs:
        return 0

    adapter = BossDetailAdapter()
    filled = 0

    for job in jobs:
        result = await adapter.fetch_description(
            job.job_id,
            job.url.split("/")[-1].replace(".html", "") if job.url else "",
        )
        if result.get("description"):
            async with AsyncSessionLocal() as db:
                j = await db.get(Job, job.job_id)
                if j:
                    j.description = result["description"]
                    await db.commit()
                    filled += 1

        await asyncio.sleep(random.uniform(2, 5))  # Be gentle

    return filled
```

- [ ] **Step 4: Test detail scraping with a known job_id**

```python
# backend/tests/test_boss_detail.py

@pytest.mark.asyncio
async def test_fetch_description():
    from app.platforms.boss_detail import BossDetailAdapter
    adapter = BossDetailAdapter()
    result = await adapter.fetch_description(
        "h27oU1rfWMJtb-n1cMmg1-mXMY6hdlm0NlqiR7wpJR49kUDfh7sfnIWADxOjzsGD",
    )
    assert "error" not in result or result.get("description")
```

- [ ] **Step 5: Run tests**

```bash
cd backend && pytest tests/test_boss_detail.py -v
cd backend && pytest tests/ -q --ignore=tests/test_integration_realdb.py --ignore=tests/screenshots
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/platforms/boss_detail.py \
        backend/app/services/job_crawl.py \
        backend/tests/test_boss_detail.py
git commit -m "feat: add job description scraping via detail API"
```

---

## Execution Order

```
Tasks 1 + 3 (run in parallel) ──> Task 2 (Frontend verify)
                                     │
Task 4 (Dedup grace) ──────────────┤
                                     │
Task 5 (Detail crawl) ─────────────┘
```

Tasks 1 (Cron expose) and 3 (Multi-config) are independent and can run in parallel.
Task 2 (Frontend verify) depends on Task 1 being complete.
Task 4 (Dedup grace) depends on Task 1 (needs new schema fields).
Task 5 (Detail crawl) is independent of Tasks 1-4 — only requires the existing boss.py pattern working.

## Self-Review

**1. Spec coverage:** All 5 points from the discussion are covered — cron (Task 1), frontend verify (Task 2), multi-config (Task 3), dedup (Task 4), detail crawl (Task 5).

**2. Placeholder scan:** Task 5 Step 1 is a diagnostic — the API endpoint is tested at runtime. The discovered endpoint is then used in Steps 2-6. Task 5 has a ⚠️ BLOCKER warning: Step 1 MUST succeed before proceeding. No other TBDs remain.

**3. Type consistency:** `consecutive_miss_count` is defined as `Integer` in Task 4 Step 1 and referenced as `job.consecutive_miss_count` in Step 4. `deactivation_threshold` is defined on `JobSearchConfig` in Step 2 and used in Step 4. `BossDetailAdapter.fetch_description()` returns `dict[str, Any]` in Step 2 and is consumed in Step 3 with the same shape. All consistent.

**4. Scope creep check:** No major scope creep detected. Each task has a clear deliverable. All user corrections have been incorporated.

**5. Completeness check:** Plan is now complete. All decision points have been resolved:
- ✅ Schema names corrected (UserConfigResponse/Update)
- ✅ croniter replaced with APScheduler CronTrigger validation
- ✅ Module-level `trigger_job_crawl()` in `scheduler_job.py` (not local to main.py)
- ✅ `_rebuild_job_crawl_scheduler_job()` in config.py
- ✅ Task 1 Step 3 frontend refactored to CronSettings component (not JobConfigForm)
- ✅ Task 5 BLOCKER warning added
- ✅ Task 4 Step 4b regression test added
- ✅ Task 1 Step 4b automated test added
- ✅ Job model already has `description` column (no new column needed)
- ✅ JobConfigForm is per-config, not global cron settings
- ✅ inter-config delay confirmed
- ✅ `random` import already exists in boss.py

---

## Architecture Decisions

1. **Module-level trigger function** (`scheduler_job.py`): Both `main.py` and `config.py` need to reference the same APScheduler job function. A local function in `main.py` can't be imported by `config.py`. Solution: define `trigger_job_crawl()` in `scheduler_job.py` at module level.

2. **Independent PUT endpoint for cron** (not merged into PATCH /config): The cron field is a separate API (`PUT /config/job-crawl-cron`) because the frontend needs a dedicated call for cron changes without touching other config fields.

3. **APScheduler CronTrigger for validation** (not croniter): `croniter` is not in requirements.txt. APScheduler's own CronTrigger.from_crontab() can validate via try/except.

4. **Cron field in dedicated settings** (not in JobConfigForm): JobConfigForm is per-config (one form per JobSearchConfig). The cron setting is global (one value for all job crawls). Wrong place to put it.

5. **Task 5 BLOCKER**: The detail API endpoint (`wapi/zpgeek/job/detail.json`) is unverified. Step 1 must succeed before proceeding.
