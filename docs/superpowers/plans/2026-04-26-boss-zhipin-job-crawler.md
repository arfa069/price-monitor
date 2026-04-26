# Boss直聘职位爬取系统实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有价格监控系统的基础上，新增 boss 直聘职位搜索爬取功能。复用 CDP 模式，批量抓取搜索列表页，去重存储，新职位飞书通知。

**Architecture:** 新增 `BossZhipinAdapter` 继承 `BasePlatformAdapter`，新增 `JobSearchConfig`/`Job` 模型，新增 `/jobs` 路由，复用现有 APScheduler 调度器和 CrawlLog 日志体系。职位爬取与价格爬取共享同一套 CDP 基础设施，独立 cron 配置。

**Tech Stack:** Python 3.11+ · FastAPI · SQLAlchemy (async) · Playwright · PostgreSQL · APScheduler · 飞书 Webhook

---

## 文件结构

```
app/
├── models/
│   ├── job.py              # JobSearchConfig, Job 模型 (CREATE)
│   └── user.py             # User.job_crawl_cron (MODIFY)
├── platforms/
│   └── boss.py             # BossZhipinAdapter (CREATE)
├── services/
│   ├── job_crawl.py        # process_job_results, crawl_all_job_searches, parse_salary (CREATE)
│   └── notification.py     # send_new_job_notification (MODIFY)
├── routers/
│   └── jobs.py             # /jobs 路由 (CREATE)
├── schemas/
│   └── job.py              # Pydantic schemas (CREATE)
└── main.py                 # 调度器新增 job_crawl_cron 任务 (MODIFY)

alembic/versions/
└── xxx_add_job_tables.py    # 迁移文件 (CREATE)

tests/
└── test_job_crawl.py       # 测试文件 (CREATE)
```

---

## Task 1: 数据库迁移

**Files:**
- Create: `alembic/versions/xxxx_add_job_tables.py`

- [ ] **Step 1: 创建迁移文件**

Run: `alembic revision --autogenerate -m "add job tables: job_search_configs and jobs"`

Expected: 生成迁移文件包含 `job_search_configs` 和 `jobs` 表

手动编辑迁移文件，确保包含以下内容：

```python
"""add job tables: job_search_configs and jobs

Revision ID: xxxx
Revises: xxxx
Create Date: 2026-04-26

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers
revision = 'xxxx'
down_revision = 'xxxx'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # job_search_configs 表
    op.create_table(
        'job_search_configs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('keyword', sa.String(length=200), nullable=True),
        sa.Column('city_code', sa.String(length=20), nullable=True),
        sa.Column('salary_min', sa.Integer(), nullable=True),
        sa.Column('salary_max', sa.Integer(), nullable=True),
        sa.Column('experience', sa.String(length=50), nullable=True),
        sa.Column('education', sa.String(length=50), nullable=True),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('notify_on_new', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # jobs 表
    op.create_table(
        'jobs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('job_id', sa.String(length=100), nullable=False),
        sa.Column('search_config_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=300), nullable=True),
        sa.Column('company', sa.String(length=200), nullable=True),
        sa.Column('company_id', sa.String(length=100), nullable=True),
        sa.Column('salary', sa.String(length=100), nullable=True),
        sa.Column('salary_min', sa.Integer(), nullable=True),
        sa.Column('salary_max', sa.Integer(), nullable=True),
        sa.Column('location', sa.String(length=200), nullable=True),
        sa.Column('experience', sa.String(length=100), nullable=True),
        sa.Column('education', sa.String(length=100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('url', sa.Text(), nullable=True),
        sa.Column('first_seen_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.ForeignKeyConstraint(['search_config_id'], ['job_search_configs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('job_id'),
    )
    op.create_index('ix_jobs_job_id', 'jobs', ['job_id'])
    op.create_index('ix_jobs_search_config_id', 'jobs', ['search_config_id'])

    # User 表新增 job_crawl_cron 列（直接用 SQLite 兼容写法）
    op.add_column('users', sa.Column('job_crawl_cron', sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'job_crawl_cron')
    op.drop_table('jobs')
    op.drop_table('job_search_configs')
```

- [ ] **Step 2: 运行迁移**

Run: `alembic upgrade head`
Expected: `Running upgrade  -> xxxx` (迁移成功)

- [ ] **Step 3: Commit**

```bash
git add alembic/versions/xxxx_add_job_tables.py
git commit -m "feat(jobs): add job_search_configs and jobs tables"
```

---

## Task 2: 数据模型

**Files:**
- Create: `app/models/job.py`
- Modify: `app/models/user.py` (新增 job_crawl_cron 字段)

> User.job_crawl_cron 已在 Task 1 迁移中通过 op.add_column 添加，此处只展示 model 定义供参考（无需修改，SQLAlchemy 会自动读取新增列）。

- [ ] **Step 1: 写入 app/models/job.py**

```python
"""Job models for boss zhipin job crawling."""
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class JobSearchConfig(Base, TimestampMixin):
    """Job search configuration for scheduled crawling."""
    __tablename__ = "job_search_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    keyword = Column(String(200), nullable=True)
    city_code = Column(String(20), nullable=True)
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    experience = Column(String(50), nullable=True)
    education = Column(String(50), nullable=True)
    url = Column(Text, nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    notify_on_new = Column(Boolean, nullable=False, default=True)

    # Relationships
    jobs = relationship("Job", back_populates="search_config", cascade="all, delete-orphan")


class Job(Base):
    """Individual job posting from boss zhipin."""
    __tablename__ = "jobs"
    __table_args__ = (
        Index("ix_jobs_job_id", "job_id"),
        Index("ix_jobs_search_config_id", "search_config_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(100), nullable=False, unique=True)  # boss's encryptJobId
    search_config_id = Column(Integer, ForeignKey("job_search_configs.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(300), nullable=True)
    company = Column(String(200), nullable=True)
    company_id = Column(String(100), nullable=True)
    salary = Column(String(100), nullable=True)
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    location = Column(String(200), nullable=True)
    experience = Column(String(100), nullable=True)
    education = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    url = Column(Text, nullable=True)
    first_seen_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    last_updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    search_config = relationship("JobSearchConfig", back_populates="jobs")
```

- [ ] **Step 2: Commit**

```bash
git add app/models/job.py
git commit -m "feat(jobs): add JobSearchConfig and Job models"
```

---

## Task 3: Pydantic Schemas

**Files:**
- Create: `app/schemas/job.py`

- [ ] **Step 1: 写入 app/schemas/job.py**

```python
"""Pydantic schemas for job-related API endpoints."""
from datetime import datetime

from pydantic import BaseModel, Field


class JobSearchConfigCreate(BaseModel):
    """Schema for creating a job search config."""
    name: str = Field(..., max_length=100, description="配置名称，如'北京 Python 职位'")
    keyword: str | None = Field(default=None, max_length=200, description="搜索关键词")
    city_code: str | None = Field(default=None, max_length=20, description="boss 直聘城市代码")
    salary_min: int | None = Field(default=None, ge=0, description="最低薪资（K）")
    salary_max: int | None = Field(default=None, ge=0, description="最高薪资（K）")
    experience: str | None = Field(default=None, max_length=50, description="经验要求")
    education: str | None = Field(default=None, max_length=50, description="学历要求")
    url: str = Field(..., description="boss 直聘搜索页完整 URL")
    active: bool = Field(default=True, description="是否启用定时爬取")
    notify_on_new: bool = Field(default=True, description="新职位是否发送通知")


class JobSearchConfigUpdate(BaseModel):
    """Schema for updating a job search config."""
    name: str | None = Field(default=None, max_length=100)
    keyword: str | None = Field(default=None, max_length=200)
    city_code: str | None = Field(default=None, max_length=20)
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    experience: str | None = Field(default=None, max_length=50)
    education: str | None = Field(default=None, max_length=50)
    url: str | None = None
    active: bool | None = None
    notify_on_new: bool | None = None


class JobSearchConfigResponse(BaseModel):
    """Schema for job search config response."""
    id: int
    user_id: int
    name: str
    keyword: str | None
    city_code: str | None
    salary_min: int | None
    salary_max: int | None
    experience: str | None
    education: str | None
    url: str
    active: bool
    notify_on_new: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobResponse(BaseModel):
    """Schema for job response."""
    id: int
    job_id: str
    search_config_id: int
    title: str | None
    company: str | None
    company_id: str | None
    salary: str | None
    salary_min: int | None
    salary_max: int | None
    location: str | None
    experience: str | None
    education: str | None
    description: str | None
    url: str | None
    first_seen_at: datetime
    last_updated_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}


class JobCrawlResult(BaseModel):
    """Schema for job crawl result."""
    total_scanned: int
    new_count: int
    updated_count: int
    deactivated_count: int = 0
```

- [ ] **Step 2: Commit**

```bash
git add app/schemas/job.py
git commit -m "feat(jobs): add Pydantic schemas for job API"
```

---

## Task 4: BossZhipinAdapter

**Files:**
- Create: `app/platforms/boss.py`
- Modify: `app/platforms/__init__.py` (导出 BossZhipinAdapter)

- [ ] **Step 1: 写入 app/platforms/boss.py**

```python
"""Boss Zhipin platform adapter for job list crawling."""
import asyncio
from typing import Any

from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from app.platforms.base import BasePlatformAdapter


class BossZhipinAdapter(BasePlatformAdapter):
    """Adapter for Boss Zhipin job search list crawling.

    Reuses BasePlatformAdapter's CDP browser lifecycle.
    Does NOT use extract_price/title (single-product interface).
    """

    async def extract_price(self, page) -> dict[str, Any]:
        """Not used for job crawler."""
        raise NotImplementedError("BossZhipinAdapter does not support price extraction")

    async def extract_title(self, page) -> str:
        """Not used for job crawler."""
        raise NotImplementedError("BossZhipinAdapter does not support title extraction")

    async def crawl(self, url: str) -> dict[str, Any]:
        """Crawl a boss zhipin job search list page.

        Returns:
            {
                "success": bool,
                "jobs": list[dict],  # extracted job data
                "count": int,
            }
        """
        await self._init_browser()

        try:
            async with asyncio.timeout(90):
                await self._page.goto(url, wait_until="domcontentloaded", timeout=45000)

                # Wait for job card list to appear
                await self._page.wait_for_selector(
                    ".job-list-box .job-card-wrapper",
                    timeout=20000,
                )

                # Scroll to load more jobs (infinite scroll)
                await self._scroll_to_load_more(max_scrolls=5)

                # Extract all job cards
                jobs = await self._extract_jobs(self._page)

                return {
                    "success": True,
                    "jobs": jobs,
                    "count": len(jobs),
                }

        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "Crawl timeout: page took longer than 90s to respond",
            }
        except PlaywrightTimeoutError as e:
            return {
                "success": False,
                "error": f"Page load timeout: {e}",
            }
        except (ConnectionError, OSError) as e:
            return {
                "success": False,
                "error": f"Network error: {e}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {e}",
            }
        finally:
            await self._close_browser()

    async def _scroll_to_load_more(self, max_scrolls: int = 5) -> None:
        """Scroll down to trigger lazy loading of more job cards.

        Boss Zhipin uses infinite scroll - each scroll loads ~30 more jobs.
        Terminates early if no new jobs appear after a scroll.
        """
        for _ in range(max_scrolls):
            previous_count = await self._page.evaluate(
                "() => document.querySelectorAll('.job-card-wrapper').length"
            )
            await self._page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await self._page.wait_for_timeout(1500)
            current_count = await self._page.evaluate(
                "() => document.querySelectorAll('.job-card-wrapper').length"
            )
            if current_count == previous_count:
                # No new jobs loaded, stop scrolling
                break

    async def _extract_jobs(self, page) -> list[dict]:
        """Extract job data from all visible job cards using page.evaluate.

        Faster than using Playwright locators one by one.
        """
        return await page.evaluate("""
            () => {
                const cards = document.querySelectorAll('.job-card-wrapper');
                return Array.from(cards).map(card => {
                    // Try to get job_id from data attribute or onclick
                    let jobId = card.getAttribute('data-jobid') || '';
                    if (!jobId) {
                        const link = card.querySelector('a');
                        if (link) {
                            const match = link.href.match(/job_detail\\/([^.]+)/);
                            if (match) jobId = match[1];
                        }
                    }

                    // Get company info
                    let companyId = '';
                    const companyEl = card.querySelector('.company-info');
                    if (companyEl) {
                        const match = companyEl.getAttribute('data-lid') ||
                                      companyEl.getAttribute('data-jobid');
                        if (match) companyId = match;
                    }

                    // Get tags (experience, education)
                    const tagEls = card.querySelectorAll('.tag-list li');
                    const tags = Array.from(tagEls).map(el => el.innerText.trim());

                    // Get salary
                    const salaryEl = card.querySelector('.salary');
                    const salary = salaryEl ? salaryEl.innerText.trim() : '';

                    // Get area
                    const areaEl = card.querySelector('.job-area');
                    const area = areaEl ? areaEl.innerText.trim() : '';

                    // Get job link
                    const linkEl = card.querySelector('a');
                    const jobUrl = linkEl ? linkEl.href : '';

                    return {
                        job_id: jobId,
                        title: (card.querySelector('.job-name') || {}).innerText || '',
                        company: (card.querySelector('.company-name') || {}).innerText || '',
                        company_id: companyId,
                        salary: salary,
                        location: area,
                        experience: tags[0] || '',
                        education: tags[1] || '',
                        url: jobUrl,
                    };
                });
            }
        """)
```

- [ ] **Step 2: 修改 app/platforms/__init__.py，追加导出**

```python
from app.platforms.amazon import AmazonAdapter
from app.platforms.boss import BossZhipinAdapter  # 新增
from app.platforms.jd import JDAdapter
from app.platforms.taobao import TaobaoAdapter

__all__ = [
    "AmazonAdapter",
    "BossZhipinAdapter",  # 新增
    "JDAdapter",
    "TaobaoAdapter",
]
```

- [ ] **Step 3: Commit**

```bash
git add app/platforms/boss.py app/platforms/__init__.py
git commit -m "feat(jobs): add BossZhipinAdapter for job list crawling"
```

---

## Task 5: 职位爬取服务

**Files:**
- Create: `app/services/job_crawl.py`
- Modify: `app/services/notification.py`

- [ ] **Step 1: 写入 app/services/job_crawl.py**

```python
"""Job crawling service: process results, deduplicate, send notifications."""
import logging
import re
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.crawl_log import CrawlLog
from app.models.job import Job, JobSearchConfig
from app.services.notification import send_new_job_notification

logger = logging.getLogger(__name__)


def parse_salary(salary_str: str | None) -> tuple[int | None, int | None]:
    """Parse salary string like '20-40K·14薪' to (min, max) in K.

    Returns:
        (salary_min, salary_max) in units of K, or (None, None) if unparseable.
    """
    if not salary_str:
        return None, None

    # Remove bonus part like "·14薪"
    salary_str = re.sub(r'·\d+薪', '', salary_str)

    # Match patterns like "20-40K", "20K", "20-40k", "面议"
    if salary_str in ('面议', '薪资面议', '薪资面议 '):
        return None, None

    match = re.match(r'(\d+)[kK]?-(\d+)[kK]?', salary_str)
    if match:
        return int(match.group(1)), int(match.group(2))

    # Single value like "20K"
    match = re.match(r'^(\d+)[kK]?$', salary_str.strip())
    if match:
        val = int(match.group(1))
        return val, val

    return None, None


async def process_job_results(
    config_id: int,
    jobs: list[dict],
    total_scraped: int,
) -> dict:
    """Process crawl results: deduplicate, insert/update jobs, send notifications.

    Args:
        config_id: The JobSearchConfig ID that was crawled
        jobs: List of job data dicts from BossZhipinAdapter
        total_scraped: Total number of jobs seen in this crawl (for logging)

    Returns:
        {"new_count": N, "updated_count": N, "deactivated_count": N}
    """
    new_count = 0
    updated_count = 0
    deactivated_count = 0

    async with AsyncSessionLocal() as db:
        config = await db.get(JobSearchConfig, config_id)
        if not config:
            logger.warning(f"JobSearchConfig {config_id} not found")
            return {"new_count": 0, "updated_count": 0, "deactivated_count": 0}

        # Get job_ids seen in this crawl
        seen_job_ids = {job["job_id"] for job in jobs if job.get("job_id")}

        # Deactivate jobs that were seen last time but not this time
        if seen_job_ids:
            result = await db.execute(
                select(Job).where(
                    Job.search_config_id == config_id,
                    Job.is_active == True,
                )
            )
            all_active_jobs = list(result.scalars().all())

            for job in all_active_jobs:
                if job.job_id not in seen_job_ids:
                    job.is_active = False
                    job.last_updated_at = datetime.now(UTC)
                    deactivated_count += 1

        # Process each scraped job
        for job_data in jobs:
            job_id = job_data.get("job_id")
            if not job_id:
                continue

            result = await db.execute(
                select(Job).where(Job.job_id == job_id)
            )
            existing = result.scalar_one_or_none()

            salary = job_data.get("salary")
            salary_min, salary_max = parse_salary(salary)

            if existing:
                # Update existing job
                existing.last_updated_at = datetime.now(UTC)
                existing.is_active = True
                # Update fields if changed
                if job_data.get("title"):
                    existing.title = job_data["title"]
                if job_data.get("company"):
                    existing.company = job_data["company"]
                if salary:
                    existing.salary = salary
                    existing.salary_min = salary_min
                    existing.salary_max = salary_max
                if job_data.get("location"):
                    existing.location = job_data["location"]
                if job_data.get("experience"):
                    existing.experience = job_data["experience"]
                if job_data.get("education"):
                    existing.education = job_data["education"]
                if job_data.get("url"):
                    existing.url = job_data["url"]
                updated_count += 1
            else:
                # Insert new job
                new_job = Job(
                    job_id=job_id,
                    search_config_id=config_id,
                    title=job_data.get("title") or "",
                    company=job_data.get("company") or "",
                    company_id=job_data.get("company_id") or "",
                    salary=salary or "",
                    salary_min=salary_min,
                    salary_max=salary_max,
                    location=job_data.get("location") or "",
                    experience=job_data.get("experience") or "",
                    education=job_data.get("education") or "",
                    url=job_data.get("url") or "",
                    first_seen_at=datetime.now(UTC),
                    last_updated_at=datetime.now(UTC),
                    is_active=True,
                )
                db.add(new_job)
                new_count += 1

        # Send notification for new jobs (after commit so config.notify_on_new is available)
        if new_count > 0 and config.notify_on_new:
            try:
                await send_new_job_notification(config, new_count, total_scraped)
            except Exception:
                logger.exception("Failed to send job notification for config %s", config_id)

        # Log crawl result — in same transaction as job inserts/updates
        crawl_log = CrawlLog(
            product_id=config_id,
            platform="boss",
            status="SUCCESS",
            price=Decimal(new_count),
            currency=None,
            timestamp=datetime.now(UTC),
            error_message=None,
        )
        db.add(crawl_log)

        # Single commit for both job data and crawl log
        await db.commit()

    return {
        "new_count": new_count,
        "updated_count": updated_count,
        "deactivated_count": deactivated_count,
    }


async def crawl_single_config(config_id: int) -> dict:
    """Crawl a single JobSearchConfig and process results."""
    from app.platforms import BossZhipinAdapter
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        config = await db.get(JobSearchConfig, config_id)
        if not config:
            return {"status": "error", "error": "Config not found"}

    adapter = BossZhipinAdapter()
    result = await adapter.crawl(config.url)

    if result.get("success"):
        stats = await process_job_results(
            config_id=config_id,
            jobs=result["jobs"],
            total_scraped=result["count"],
        )
        return {"status": "success", **stats}
    else:
        # Log error
        async with AsyncSessionLocal() as db:
            log = CrawlLog(
                product_id=config_id,
                platform="boss",
                status="ERROR",
                price=None,
                currency=None,
                timestamp=datetime.now(UTC),
                error_message=result.get("error", "Unknown error"),
            )
            db.add(log)
            await db.commit()
        return {"status": "error", "error": result.get("error")}


async def crawl_all_job_searches(source: str = "manual") -> dict:
    """Crawl all active job search configs."""
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(JobSearchConfig).where(JobSearchConfig.active == True)
        )
        configs = list(result.scalars().all())

    if not configs:
        return {"status": "completed", "total": 0, "success": 0, "errors": 0}

    total = len(configs)
    success_count = 0
    error_count = 0
    details = []

    for config in configs:
        result = await crawl_single_config(config.id)
        details.append({"config_id": config.id, **result})
        if result.get("status") == "success":
            success_count += 1
        else:
            error_count += 1

    return {
        "status": "completed",
        "total": total,
        "success": success_count,
        "errors": error_count,
        "details": details,
    }
```

> **修正 1（已采纳）：** `process_job_results` 中的两个 DB session 合并为单个 session。CrawlLog 写入移到第一个 `async with` 块里，`return` 前统一 `await db.commit()`。消除原子性风险。

> **修正 2（已采纳）：** `notification.py` 顶部加 `from __future__ import annotations`，确保前向引用类型标注在运行时正确解析。

> **修正 3（已采纳）：** `_trigger_crawl_jobs` 在 `_start_scheduler` 函数**开头**定义（函数提升），然后 `scheduler.add_job` 正常引用。

- [ ] **Step 2: 修改 app/services/notification.py，追加新职位通知函数**

在文件顶部追加一行（修正 2）：
```python
from __future__ import annotations
```

在 `send_feishu_notification` 函数后追加：

在 `send_feishu_notification` 函数后追加：

```python
async def send_new_job_notification(
    config: "JobSearchConfig",
    new_job_count: int,
    total_scraped: int,
) -> dict:
    """Send Feishu notification for newly discovered jobs.

    Args:
        config: The JobSearchConfig that was crawled
        new_job_count: Number of new jobs found
        total_scraped: Total number of jobs scraped this run

    Returns:
        Response from Feishu API
    """
    from app.models.user import User
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        user_result = await db.execute(select(User).where(User.id == 1))
        user = user_result.scalar_one_or_none()

    if not user or not user.feishu_webhook_url:
        return {"status": "skipped", "reason": "no_webhook"}

    message = f"""🔔 Boss直聘新职位提醒

搜索配置：{config.name}
本次发现 {new_job_count} 个新职位（共扫描 {total_scraped} 个）

---
共收录职位请查看管理后台"""

    return await send_feishu_notification(user.feishu_webhook_url, message)
```

> 注意：`send_new_job_notification` 末尾调用 `send_feishu_notification`，需要在函数内 import 避免循环依赖。

- [ ] **Step 3: Commit**

```bash
git add app/services/job_crawl.py app/services/notification.py
git commit -m "feat(jobs): add job crawling service with deduplication and notifications"
```

---

## Task 6: /jobs API 路由

**Files:**
- Create: `app/routers/jobs.py`
- Modify: `app/main.py` (注册路由)

- [ ] **Step 1: 写入 app/routers/jobs.py**

```python
"""Job search API router."""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy import asc, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.job import Job, JobSearchConfig
from app.models.user import User
from app.schemas.job import (
    JobCrawlResult,
    JobResponse,
    JobSearchConfigCreate,
    JobSearchConfigResponse,
    JobSearchConfigUpdate,
)
from app.services.job_crawl import crawl_all_job_searches, crawl_single_config

router = APIRouter(prefix="/jobs", tags=["jobs"])


# ── JobSearchConfig CRUD ──────────────────────────────────────────

@router.get("/configs", response_model=list[JobSearchConfigResponse])
async def list_configs(
    active: bool | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List all job search configs."""
    query = select(JobSearchConfig).where(JobSearchConfig.user_id == 1)
    if active is not None:
        query = query.where(JobSearchConfig.active == active)
    query = query.order_by(desc(JobSearchConfig.created_at))
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/configs", response_model=JobSearchConfigResponse, status_code=201)
async def create_config(
    data: JobSearchConfigCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new job search config."""
    config = JobSearchConfig(
        user_id=1,
        **data.model_dump(),
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return config


@router.get("/configs/{config_id}", response_model=JobSearchConfigResponse)
async def get_config(config_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single config."""
    result = await db.execute(
        select(JobSearchConfig).where(
            JobSearchConfig.id == config_id,
            JobSearchConfig.user_id == 1,
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    return config


@router.patch("/configs/{config_id}", response_model=JobSearchConfigResponse)
async def update_config(
    config_id: int,
    data: JobSearchConfigUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a config."""
    result = await db.execute(
        select(JobSearchConfig).where(
            JobSearchConfig.id == config_id,
            JobSearchConfig.user_id == 1,
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)

    await db.commit()
    await db.refresh(config)
    return config


@router.delete("/configs/{config_id}")
async def delete_config(config_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a config (cascades to jobs)."""
    result = await db.execute(
        select(JobSearchConfig).where(
            JobSearchConfig.id == config_id,
            JobSearchConfig.user_id == 1,
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")

    await db.delete(config)
    await db.commit()
    return {"message": "Config deleted"}


# ── Job Listing ──────────────────────────────────────────────────

@router.get("", response_model=list[JobResponse])
async def list_jobs(
    search_config_id: int | None = None,
    keyword: str | None = None,
    company: str | None = None,
    salary_min: int | None = None,
    salary_max: int | None = None,
    location: str | None = None,
    is_active: bool | None = None,
    sort_by: str = Query(default="first_seen_at"),
    sort_order: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List jobs with filtering and pagination."""
    # Join with JobSearchConfig to filter by user_id=1
    query = select(Job).join(JobSearchConfig).where(JobSearchConfig.user_id == 1)

    if search_config_id is not None:
        query = query.where(Job.search_config_id == search_config_id)
    if keyword:
        query = query.where(
            Job.title.ilike(f"%{keyword}%") |
            Job.company.ilike(f"%{keyword}%") |
            Job.description.ilike(f"%{keyword}%")
        )
    if company:
        query = query.where(Job.company.ilike(f"%{company}%"))
    if salary_min is not None:
        query = query.where(Job.salary_min >= salary_min)
    if salary_max is not None:
        query = query.where(Job.salary_max <= salary_max)
    if location:
        query = query.where(Job.location.ilike(f"%{location}%"))
    if is_active is not None:
        query = query.where(Job.is_active == is_active)

    # Sorting
    sort_column = {
        "first_seen_at": Job.first_seen_at,
        "last_updated_at": Job.last_updated_at,
        "salary_min": Job.salary_min,
    }.get(sort_by, Job.first_seen_at)
    if sort_order == "asc":
        query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(sort_column))

    # Pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{job_id_str}", response_model=JobResponse)
async def get_job(job_id_str: str, db: AsyncSession = Depends(get_db)):
    """Get a single job by boss job_id."""
    result = await db.execute(
        select(Job).join(JobSearchConfig).where(
            Job.job_id == job_id_str,
            JobSearchConfig.user_id == 1,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


# ── Crawl Triggers ───────────────────────────────────────────────

@router.post("/crawl-now")
async def crawl_now():
    """Trigger crawling all active job search configs."""
    result = await crawl_all_job_searches(source="manual")
    return JSONResponse(content={
        "status": result["status"],
        "total": result["total"],
        "success": result["success"],
        "errors": result["errors"],
    })


@router.post("/crawl-now/{config_id}", response_model=JobCrawlResult)
async def crawl_single(config_id: int):
    """Trigger crawling a single config."""
    result = await crawl_single_config(config_id)
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("error"))
    return JobCrawlResult(**result)
```

- [ ] **Step 2: 修改 app/main.py，在 router 注册部分追加**

在现有的 `app.include_router(crawl.router)` 后追加一行：

```python
from app.routers.jobs import router as jobs_router  # 新增

# ... existing routers ...
app.include_router(jobs_router)  # 新增
```

- [ ] **Step 3: Commit**

```bash
git add app/routers/jobs.py app/main.py
git commit -m "feat(jobs): add /jobs API router for job search configs and crawl triggers"
```

---

## Task 7: 调度器集成

**Files:**
- Modify: `app/main.py` (_start_scheduler 函数中注册 job_crawl_cron 任务)

- [ ] **Step 1: 修改 app/main.py 的 _start_scheduler 函数**

在文件顶部 import 区追加（如果还没有）：

```python
# 职位爬取定时任务在 _start_scheduler 开头定义
```

在 `_start_scheduler` 函数**开头**定义 `_trigger_crawl_jobs`（使用函数提升，Python 允许先调用后定义）：

```python
async def _trigger_crawl_jobs():
    """APScheduler job: crawl all active job searches (runs as background task)."""
    from app.services.job_crawl import crawl_all_job_searches
    logger.info("Job crawl cron triggered")
    asyncio.create_task(crawl_all_job_searches(source="cron"))
```

在 `scheduler.add_job(_trigger_crawl_all, ...)` 后面追加职位爬取定时任务：

```python
# 职位爬取定时任务
job_crawl_job_id = "job_crawl_cron_job"
try:
    tz = zoneinfo.ZoneInfo(user.crawl_timezone or "Asia/Shanghai")
    # 职位爬取使用独立的 job_crawl_cron，默认为每天早上 9 点
    job_cron = user.job_crawl_cron or "0 9 * * *"
    scheduler.add_job(
        _trigger_crawl_jobs,
        trigger=CronTrigger.from_crontab(job_cron, timezone=tz),
        id=job_crawl_job_id,
        name="Crawl all active job searches",
        replace_existing=True,
        max_instances=1,
    )
    logger.info(
        "Registered job_crawl_cron_job with schedule '%s' (tz=%s)",
        job_cron, tz,
    )
except Exception:
    logger.exception("Failed to register job_crawl_cron job")
```

在 `_stop_scheduler` 中追加关闭 boss 适配器浏览器实例。在 `_cleanup_all_shared_browsers` 中修改：

```python
from app.platforms import BossZhipinAdapter  # 在 _cleanup_all_shared_browsers 函数内
for adapter_class in [TaobaoAdapter, JDAdapter, AmazonAdapter, BossZhipinAdapter]:
```

- [ ] **Step 2: Commit**

```bash
git add app/main.py
git commit -m "feat(jobs): integrate job_crawl_cron into APScheduler"
```

---

## Task 8: 测试

**Files:**
- Create: `tests/test_job_crawl.py`

- [ ] **Step 1: 写入 tests/test_job_crawl.py**

```python
"""Tests for job crawling service."""
import pytest
from app.services.job_crawl import parse_salary


class TestParseSalary:
    """Test salary string parsing."""

    def test_parse_salary_range_k(self):
        assert parse_salary("20-40K") == (20, 40)
        assert parse_salary("15-30k") == (15, 30)

    def test_parse_salary_with_bonus(self):
        assert parse_salary("20-40K·14薪") == (20, 40)
        assert parse_salary("30-50K·16薪") == (30, 50)

    def test_parse_salary_single_value(self):
        assert parse_salary("25K") == (25, 25)
        assert parse_salary("15k") == (15, 15)

    def test_parse_salary_negotiable(self):
        assert parse_salary("面议") == (None, None)
        assert parse_salary("薪资面议") == (None, None)

    def test_parse_salary_none(self):
        assert parse_salary(None) == (None, None)

    def test_parse_salary_empty(self):
        assert parse_salary("") == (None, None)

    def test_parse_salary_invalid(self):
        assert parse_salary("面薪") == (None, None)
        assert parse_salary("未知格式") == (None, None)

    def test_parse_salary_edge_cases(self):
        # Leading/trailing whitespace
        assert parse_salary("  20-40K  ") == (20, 40)
        # Mixed case K
        assert parse_salary("20-40k") == (20, 40)
        # Salary with space
        assert parse_salary("20 - 40K") == (None, None)  # space breaks regex
        # Very large numbers
        assert parse_salary("100-200K") == (100, 200)


# 集成测试（需要数据库连接，标记为 skip 或用 pytest-asyncio）
@pytest.mark.skip(reason="Requires database connection")
class TestJobCrawlService:
    """Integration tests for job crawl service."""

    @pytest.mark.asyncio
    async def test_process_job_results_deduplication(self):
        """New job should be inserted, existing job should be updated."""
        from app.services.job_crawl import process_job_results

        jobs = [
            {
                "job_id": "test_job_001",
                "title": "Python开发工程师",
                "company": "测试公司",
                "salary": "20-40K·14薪",
                "location": "北京",
                "experience": "1-3年",
                "education": "本科",
                "url": "https://www.zhipin.com/job/test",
            }
        ]

        # First run: creates new job
        result = await process_job_results(config_id=1, jobs=jobs, total_scraped=1)
        assert result["new_count"] == 1
        assert result["updated_count"] == 0

        # Second run: updates existing job
        result = await process_job_results(config_id=1, jobs=jobs, total_scraped=1)
        assert result["new_count"] == 0
        assert result["updated_count"] == 1

    @pytest.mark.asyncio
    async def test_process_job_results_deactivates_missing(self):
        """Job not in new results should be marked inactive."""
        from app.services.job_crawl import process_job_results

        # First: add a job
        await process_job_results(config_id=1, jobs=[{"job_id": "orphan_job", "title": "Orphan"}], total_scraped=1)

        # Second: crawl with empty list (job no longer appears)
        result = await process_job_results(config_id=1, jobs=[], total_scraped=0)
        assert result["deactivated_count"] == 1
```

- [ ] **Step 2: 运行单元测试验证**

Run: `pytest tests/test_job_crawl.py::TestParseSalary -v`
Expected: 11 tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_job_crawl.py
git commit -m "test(jobs): add tests for salary parsing and job deduplication"
```

---

## 自检清单

- [ ] Task 1: 数据库迁移运行成功（`alembic upgrade head`）
- [ ] Task 2: `app/models/job.py` 两个模型定义完整（JobSearchConfig, Job）
- [ ] Task 3: 所有 Pydantic schema 字段与 API 设计文档一致
- [ ] Task 4: `BossZhipinAdapter.crawl()` 返回结构为 `{"success": bool, "jobs": list, "count": int}`
- [ ] Task 5: `parse_salary()` 覆盖所有薪资格式（范围、单值、面议）
- [ ] Task 5: `process_job_results()` 包含去重 + 下架检测 + 通知逻辑
- [ ] Task 6: 10 个 API 端点全部注册（4 configs CRUD + 2 jobs 列表 + 2 crawl 触发）
- [ ] Task 7: 调度器启动时不报错（可用 `uvicorn app.main:app` 启动验证）
- [ ] Task 8: `parse_salary` 测试全部通过

---

## 验收标准（完成后检查）

1. **数据库**：`alembic upgrade head` 成功，`job_search_configs` 和 `jobs` 表存在
2. **API 可用**：启动后 `GET /docs` 能看到 `/jobs` 和 `/jobs/configs` 端点
3. **手动爬取**：`POST /jobs/crawl-now/{config_id}` 能触发单个配置爬取（需 CDP 连接）
4. **去重**：`POST /jobs/crawl-now/{config_id}` 重复调用不产生重复 Job
5. **下架检测**：Job 不在爬取结果中时被标记 `is_active=False`
6. **定时调度**：`User.job_crawl_cron` 字段存在，调度器注册 `job_crawl_cron_job`
7. **飞书通知**：新职位发现时调用 `send_new_job_notification`
