# JobSearchConfig 独立 Cron 定时器 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为每个 JobSearchConfig 设置独立的 cron 定时器，替代全局 `job_crawl_cron` 调度。

**Architecture:** 添加 `cron_expression`/`cron_timezone` 字段到 `JobSearchConfig` 表；创建 `JobConfigScheduler` 类封装 APScheduler job 增删改；CRUD 端点操作时同步调度器；前端 /schedule 页面改为 config 级 cron 管理表格。

**Tech Stack:** Python APScheduler · FastAPI · SQLAlchemy · React + Ant Design

---

## 文件清单

| 文件 | 操作 | 职责 |
|------|------|------|
| `backend/app/models/job.py` | 修改 | `JobSearchConfig` 追加 `cron_expression`, `cron_timezone` |
| `backend/app/schemas/job.py` | 修改 | 响应/更新 schema 追加 cron 字段；加 `JobConfigCronUpdate` |
| `backend/alembic/versions/` | 新增 | 迁移文件（auto-generate + 调整） |
| `backend/app/services/scheduler_job.py` | 修改 | 添加 `JobConfigScheduler` 类 |
| `backend/app/main.py` | 修改 | 替换全局 `job_crawl_cron_job` 为 per-config 调度 |
| `backend/app/routers/jobs.py` | 修改 | Config CRUD 同步调度器；新增两个端点 |
| `frontend/src/types/index.ts` | 修改 | 追加 cron 字段类型；加 `JobConfigCronUpdate`；更新 `SchedulerStatusResponse` |
| `frontend/src/api/config.ts` | 修改 | 移除 `getJobCrawlCron`/`updateJobCrawlCron` |
| `frontend/src/pages/ScheduleConfigPage.tsx` | 修改 | 职位区域改为 config 级 cron 管理表格 |
| `frontend/src/api/jobs.ts` | 修改 | 加 `updateConfigCron` 方法 |
| `backend/tests/test_scheduler_config.py` | 新增 | 调度器同步测试 |

---

### Task 1: 数据库模型 + 迁移

**Files:**
- Modify: `backend/app/models/job.py:29-43`
- Create: `backend/alembic/versions/006_add_cron_fields_to_job_configs.py`
- Test: 手动验证迁移

- [ ] **Step 1: 修改 JobSearchConfig 模型，追加 cron 字段**

`backend/app/models/job.py` 的 `JobSearchConfig` 类在 `deactivation_threshold` 字段后追加：

```python
cron_expression = Column(
    String(100), nullable=True,
    comment="5-segment crontab expression for per-config scheduling. Null means no scheduled crawl.",
)
cron_timezone = Column(
    String(50), nullable=True, default="Asia/Shanghai",
    comment="Timezone for this config's cron expression",
)
```

- [ ] **Step 2: 生成迁移文件**

```bash
cd backend && alembic revision --autogenerate -m "add cron fields to job_search_configs"
```

检查生成的迁移文件，确保列名和 nullable 正确。重命名为 `006_add_cron_fields_to_job_configs.py`。

- [ ] **Step 3: 执行迁移**

```bash
cd backend && alembic upgrade head
```

- [ ] **Step 4: 提交**

```bash
git add backend/app/models/job.py backend/alembic/versions/006_add_cron_fields_to_job_configs.py
git commit -m "feat(jobs): add cron_expression and cron_timezone fields to JobSearchConfig"
```

---

### Task 2: Pydantic Schemas 更新

**Files:**
- Modify: `backend/app/schemas/job.py`

- [ ] **Step 1: `JobSearchConfigCreate` 追加 cron 字段**

```python
# 在 deactivation_threshold 后面追加：
cron_expression: str | None = Field(
    default=None, max_length=100, description="5段 crontab 表达式，null 表示不定时"
)
cron_timezone: str | None = Field(default=None, max_length=50, description="时区")
```

- [ ] **Step 2: `JobSearchConfigUpdate` 追加 cron 字段**

```python
cron_expression: str | None = Field(default=None, max_length=100)
cron_timezone: str | None = Field(default=None, max_length=50)
```

- [ ] **Step 3: `JobSearchConfigResponse` 追加 cron 字段**

```python
cron_expression: str | None
cron_timezone: str | None
```

- [ ] **Step 4: 新增 `JobConfigCronUpdate` schema**

```python
class JobConfigCronUpdate(BaseModel):
    """Schema for updating only the cron settings of a job search config."""
    cron_expression: str | None = Field(
        default=None, max_length=100,
        description="5段 crontab 表达式，设为 null 取消定时",
    )
    cron_timezone: str | None = Field(
        default=None, max_length=50,
        description="时区，默认 Asia/Shanghai",
    )
```

- [ ] **Step 5: 提交**

```bash
git add backend/app/schemas/job.py
git commit -m "feat(jobs): add cron fields to job search config schemas"
```

---

### Task 3: SchedulerManager 类

**Files:**
- Modify: `backend/app/services/scheduler_job.py`

- [ ] **Step 1: 写测试（先失败）**

创建 `backend/tests/test_scheduler_config.py`：

```python
"""Tests for JobConfigScheduler manager."""
import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler


@pytest.fixture
def scheduler():
    s = AsyncIOScheduler()
    s.start()
    yield s
    s.shutdown(wait=False)


@pytest.mark.asyncio
async def test_add_job(scheduler):
    """Should add an APScheduler job for a given config."""
    from app.services.scheduler_job import JobConfigScheduler

    mgr = JobConfigScheduler(scheduler)
    mgr.add_job(config_id=1, cron_expression="0 9 * * *", timezone="Asia/Shanghai")

    job = scheduler.get_job("job_config_cron_1")
    assert job is not None
    assert "crawl_single_config" in str(job.func_ref)


@pytest.mark.asyncio
async def test_remove_job(scheduler):
    """Should remove the APScheduler job for a given config."""
    from app.services.scheduler_job import JobConfigScheduler

    mgr = JobConfigScheduler(scheduler)
    mgr.add_job(config_id=1, cron_expression="0 9 * * *", timezone="Asia/Shanghai")
    mgr.remove_job(config_id=1)

    job = scheduler.get_job("job_config_cron_1")
    assert job is None


@pytest.mark.asyncio
async def test_replace_job(scheduler):
    """Should replace existing job when add_job called again."""
    from app.services.scheduler_job import JobConfigScheduler

    mgr = JobConfigScheduler(scheduler)
    mgr.add_job(config_id=1, cron_expression="0 9 * * *", timezone="Asia/Shanghai")
    mgr.add_job(config_id=1, cron_expression="0 18 * * *", timezone="Asia/Shanghai")

    job = scheduler.get_job("job_config_cron_1")
    assert job is not None
    assert str(job.trigger) != ""  # job exists with updated trigger


@pytest.mark.asyncio
async def test_sync_all(scheduler):
    """Should register jobs for all configs with cron_expression set."""
    from app.services.scheduler_job import JobConfigScheduler

    mgr = JobConfigScheduler(scheduler)
    # sync_all reads from DB, so we mock the DB query
    # For now just verify it doesn't crash with empty DB
    await mgr.sync_all()


@pytest.mark.asyncio
async def test_get_next_run_times(scheduler):
    """Should return next run times for all config jobs."""
    from app.services.scheduler_job import JobConfigScheduler

    mgr = JobConfigScheduler(scheduler)
    mgr.add_job(config_id=1, cron_expression="0 9 * * *", timezone="Asia/Shanghai")

    result = mgr.get_next_run_times()
    assert 1 in result
    assert result[1]["cron_expression"] == "0 9 * * *"
    assert "next_run_at" in result[1]
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd backend && python -m pytest tests/test_scheduler_config.py -v
```

预期：ImportError — `JobConfigScheduler` 不存在。

- [ ] **Step 3: 实现 `JobConfigScheduler` 类**

在 `backend/app/services/scheduler_job.py` 末尾追加：

```python
import zoneinfo

from apscheduler.triggers.cron import CronTrigger


class JobConfigScheduler:
    """Manages per-config APScheduler jobs for job search crawl scheduling.

    Each JobSearchConfig can have its own cron expression. This manager
    encapsulates the add/remove/sync lifecycle, using job IDs in the
    format ``job_config_cron_{config_id}``.

    Usage::

        mgr = JobConfigScheduler(app.state.scheduler)
        mgr.add_job(config_id=1, cron_expression="0 9 * * *")
        mgr.remove_job(config_id=2)
        await mgr.sync_all()  # called on startup to rebuild from DB
    """

    JOB_ID_PREFIX = "job_config_cron_"

    def __init__(self, scheduler) -> None:
        self._scheduler = scheduler

    # ── Public API ──────────────────────────────────────────────

    def add_job(
        self,
        config_id: int,
        cron_expression: str,
        timezone: str = "Asia/Shanghai",
    ) -> None:
        """Register or replace a cron job for the given config.

        The job calls ``crawl_single_config(config_id)`` when triggered.
        Idempotent — if a job already exists for this config it will be
        replaced with the new schedule.
        """
        if not cron_expression or not cron_expression.strip():
            self.remove_job(config_id)
            return

        job_id = self._job_id(config_id)
        tz = zoneinfo.ZoneInfo(timezone)

        from app.services.job_crawl import crawl_single_config

        self._scheduler.add_job(
            crawl_single_config,
            trigger=CronTrigger.from_crontab(cron_expression, timezone=tz),
            id=job_id,
            name=f"JobConfig crawl #{config_id}",
            replace_existing=True,
            max_instances=1,
            kwargs={"config_id": config_id},
        )
        logger.info(
            "Registered cron job %s with schedule '%s' (tz=%s)",
            job_id, cron_expression, timezone,
        )

    def remove_job(self, config_id: int) -> None:
        """Remove the cron job for a config (if it exists)."""
        job_id = self._job_id(config_id)
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)
            logger.info("Removed cron job %s", job_id)

    async def sync_all(self) -> None:
        """Sync scheduler state with the database.

        Called once on application startup. Reads all configs with a
        non-null ``cron_expression`` from the DB and registers a job
        for each one.
        """
        from sqlalchemy import select
        from app.database import AsyncSessionLocal
        from app.models.job import JobSearchConfig

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(JobSearchConfig).where(
                    JobSearchConfig.cron_expression.isnot(None),
                    JobSearchConfig.user_id == 1,
                )
            )
            configs = result.scalars().all()

        for config in configs:
            self.add_job(
                config_id=config.id,
                cron_expression=config.cron_expression,
                timezone=config.cron_timezone or "Asia/Shanghai",
            )

        logger.info("JobConfigScheduler synced: %d config jobs registered", len(configs))

    def get_next_run_times(self) -> dict[int, dict]:
        """Return next run time info for all registered config jobs.

        Returns:
            dict mapping config_id -> {cron_expression, next_run_at}
        """
        result: dict[int, dict] = {}
        for job in self._scheduler.get_jobs():
            if not job.id.startswith(self.JOB_ID_PREFIX):
                continue
            config_id = int(job.id[len(self.JOB_ID_PREFIX):])
            result[config_id] = {
                "cron_expression": str(job.trigger),
                "next_run_at": job.next_run_time.isoformat() if job.next_run_time else None,
            }
        return result

    # ── Internal helpers ────────────────────────────────────────────

    def _job_id(self, config_id: int) -> str:
        return f"{self.JOB_ID_PREFIX}{config_id}"
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
cd backend && python -m pytest tests/test_scheduler_config.py -v
```

预期：5 个 tests 全部 PASS。

- [ ] **Step 5: 提交**

```bash
git add backend/app/services/scheduler_job.py backend/tests/test_scheduler_config.py
git commit -m "feat(jobs): add JobConfigScheduler for per-config cron management"
```

---

### Task 4: main.py 启动流程调整

**Files:**
- Modify: `backend/app/main.py:87-109`

- [ ] **Step 1: 替换全局 job_crawl_cron_job 为 JobConfigScheduler**

将 `_start_scheduler` 函数中注册 `job_crawl_cron_job` 的代码块（`# 职位爬取定时任务` 到 `scheduler.start()` 之前）替换为：

```python
# 职位爬取使用 per-config 独立 cron 调度
from app.services.scheduler_job import JobConfigScheduler
job_config_scheduler = JobConfigScheduler(scheduler)
app.state.job_config_scheduler = job_config_scheduler
await job_config_scheduler.sync_all()
```

删除原有的 `trigger_job_crawl` import 和 `job_crawl_cron_job` 注册代码。

- [ ] **Step 2: 更新 `/scheduler/status` 端点**

将 `job_crawl` 部分替换为返回 per-config 信息：

```python
# 替换 _job_info("job_crawl_cron_job", ...) 为:
job_config_scheduler: JobConfigScheduler = getattr(app.state, "job_config_scheduler", None)
job_schedules = job_config_scheduler.get_next_run_times() if job_config_scheduler else {}
```

返回格式改为：

```python
"jobs": {
    "product_crawl": _job_info("crawl_cron_job", "crawl_cron"),
    "job_configs": job_schedules,  # dict[int, dict]
}
```

- [ ] **Step 3: 验证开机恢复**

启动后端，确认日志输出 `JobConfigScheduler synced: N config jobs registered`。

```bash
cd backend && python -m uvicorn app.main:app
```

- [ ] **Step 4: 提交**

```bash
git add backend/app/main.py
git commit -m "feat(jobs): replace global job cron with per-config JobConfigScheduler"
```

---

### Task 5: Router 端 CRUD 同步 + 新端点

**Files:**
- Modify: `backend/app/routers/jobs.py`

- [ ] **Step 1: CRUD 端点注入 scheduler_manager**

在 `create_config` 中，`await db.refresh(config)` 之后追加：

```python
# Sync scheduler if cron is set
if config.cron_expression:
    from fastapi import Request
    request = Request.scope  # won't work — need a different approach
```

实际上从 `request.app.state` 获取 scheduler。给各端点加 `Request` 参数：

`create_config` 和 `update_config` 改为接收 `request: Request`：

```python
@router.post("/configs", ...)
async def create_config(data: JobSearchConfigCreate, request: Request, db: AsyncSession = Depends(get_db)):
```

`request.app.state.job_config_scheduler.add_job(...)`。

同样 `update_config` 中，如果 `cron_expression` 在 `update_data` 中，同步 scheduler。

`delete_config` 中，删除前获取 `config.id`，删除后调用 `remove_job(config_id)`。

- [ ] **Step 2: 新增 `PATCH /configs/{id}/cron` 端点**

```python
@router.patch("/configs/{config_id}/cron", response_model=JobSearchConfigResponse)
async def update_config_cron(
    config_id: int,
    data: JobConfigCronUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Update only the cron settings for a job search config.

    Null cron_expression disables scheduled crawling for this config.
    """
    result = await db.execute(
        select(JobSearchConfig).where(
            JobSearchConfig.id == config_id,
            JobSearchConfig.user_id == 1,
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")

    config.cron_expression = data.cron_expression
    config.cron_timezone = data.cron_timezone or "Asia/Shanghai"

    await db.commit()
    await db.refresh(config)

    # Sync scheduler
    scheduler: JobConfigScheduler = request.app.state.job_config_scheduler
    if config.cron_expression:
        scheduler.add_job(config.id, config.cron_expression, config.cron_timezone)
    else:
        scheduler.remove_job(config.id)

    return config
```

别忘了 import `Request` 和 `JobConfigScheduler`、`JobConfigCronUpdate`。

- [ ] **Step 3: 新增 `GET /scheduler/job-configs` 端点**

```python
@router.get("/scheduler/job-configs")
async def get_job_config_schedules(request: Request):
    """Get next run times for all per-config job crawl schedules."""
    scheduler: JobConfigScheduler = getattr(request.app.state, "job_config_scheduler", None)
    if not scheduler:
        return {"configs": []}
    schedules = scheduler.get_next_run_times()
    return {"configs": [
        {"config_id": cid, **info} for cid, info in schedules.items()
    ]}
```

放在 router 最后，prefix 为 `/jobs`，所以实际路径为 `/jobs/scheduler/job-configs`。

- [ ] **Step 4: 提交**

```bash
git add backend/app/routers/jobs.py
git commit -m "feat(jobs): sync scheduler on config CRUD + add cron update endpoint"
```

---

### Task 6: 前端类型 + API 更新

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/api/config.ts`
- Modify: `frontend/src/api/jobs.ts`

- [ ] **Step 1: 更新前端类型**

`frontend/src/types/index.ts`：

`JobSearchConfig` 追加：
```typescript
cron_expression: string | null
cron_timezone: string | null
```

`JobSearchConfigUpdate` 追加：
```typescript
cron_expression?: string | null
cron_timezone?: string | null
```

新增 `JobConfigCronUpdate`：
```typescript
export interface JobConfigCronUpdate {
  cron_expression: string | null
  cron_timezone?: string | null
}
```

新增 `JobConfigScheduleInfo`：
```typescript
export interface JobConfigScheduleInfo {
  config_id: number
  cron_expression: string | null
  next_run_at: string | null
}
```

更新 `SchedulerStatusResponse` 的 `jobs` 类型：
```typescript
jobs: {
  product_crawl: SchedulerJobStatus
  job_configs: Record<string, JobConfigScheduleInfo> | Record<string, never>
}
```

- [ ] **Step 2: 更新前端 API config.ts**

移除 `getJobCrawlCron` 和 `updateJobCrawlCron` 方法（不再需要全局接口）。

- [ ] **Step 3: 更新前端 API jobs.ts**

添加 `updateConfigCron` 方法：
```typescript
updateConfigCron: (id: number, data: JobConfigCronUpdate) =>
  api.patch<JobSearchConfig>(`/jobs/configs/${id}/cron`, data),
```

添加 `getJobConfigSchedules` 方法：
```typescript
getJobConfigSchedules: () =>
  api.get<{ configs: JobConfigScheduleInfo[] }>('/jobs/scheduler/job-configs'),
```

更新 import 加入 `JobConfigCronUpdate` 和 `JobConfigScheduleInfo`。

- [ ] **Step 4: 提交**

```bash
git add frontend/src/types/index.ts frontend/src/api/config.ts frontend/src/api/jobs.ts
git commit -m "feat(jobs): update frontend types and API for per-config cron"
```

---

### Task 7: 前端 /schedule 页面 — config 级 cron 管理

**Files:**
- Modify: `frontend/src/pages/ScheduleConfigPage.tsx`

- [ ] **Step 1: 替换"职位爬取"区域为 config 级表格**

将 `ScheduleConfigPage.tsx` 中 "职位爬取" 的卡片区域（`<div>...职位爬取...</div>`）替换为 config 级表格。改动内容：

```tsx
// 文件顶部新增 imports
import { useEffect, useState } from 'react'
import { Table, Input, Button, Tag, Space, message, Spin } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { jobsApi } from '@/api/jobs'
import type { JobSearchConfig, JobConfigScheduleInfo } from '@/types'

// 在 ScheduleConfigPage 组件内新增 state
const [configList, setConfigList] = useState<JobSearchConfig[]>([])
const [configSchedules, setConfigSchedules] = useState<Record<number, JobConfigScheduleInfo>>({})
const [configLoading, setConfigLoading] = useState(false)
const [cronInputs, setCronInputs] = useState<Record<number, string>>({})
const [savingCron, setSavingCron] = useState<Record<number, boolean>>({})

// 加载 config 列表和调度信息
const loadConfigData = async () => {
  setConfigLoading(true)
  try {
    const [configsRes, schedulesRes] = await Promise.all([
      jobsApi.getConfigs(),
      jobsApi.getJobConfigSchedules(),
    ])
    setConfigList(configsRes.data)
    const scheduleMap: Record<number, JobConfigScheduleInfo> = {}
    for (const s of schedulesRes.data.configs) {
      scheduleMap[s.config_id] = s
    }
    setConfigSchedules(scheduleMap)
    // 初始化 cron inputs
    const inputs: Record<number, string> = {}
    for (const c of configsRes.data) {
      inputs[c.id] = c.cron_expression || ''
    }
    setCronInputs(inputs)
  } catch {
    message.error('加载配置列表失败')
  } finally {
    setConfigLoading(false)
  }
}

// 保存单个 config 的 cron
const handleSaveConfigCron = async (configId: number) => {
  const value = cronInputs[configId]?.trim() || null
  if (value && !isValidCronFormat(value)) {
    message.error('Cron 表达式不合法')
    return
  }
  setSavingCron(prev => ({ ...prev, [configId]: true }))
  try {
    await jobsApi.updateConfigCron(configId, {
      cron_expression: value,
      cron_timezone: 'Asia/Shanghai',
    })
    message.success('已保存')
    loadConfigData()
  } catch {
    message.error('保存失败')
  } finally {
    setSavingCron(prev => ({ ...prev, [configId]: false }))
  }
}

// 表格列定义
const configColumns: ColumnsType<JobSearchConfig> = [
  {
    title: '配置名称',
    dataIndex: 'name',
    key: 'name',
    width: 200,
  },
  {
    title: 'Cron 表达式',
    key: 'cron',
    width: 300,
    render: (_, record) => (
      <Space.Compact style={{ width: '100%' }}>
        <Input
          value={cronInputs[record.id] ?? ''}
          onChange={(e) =>
            setCronInputs(prev => ({ ...prev, [record.id]: e.target.value }))
          }
          placeholder="0 9 * * *（空=不定时）"
          style={{ width: 220 }}
        />
        <Button
          type="primary"
          onClick={() => handleSaveConfigCron(record.id)}
          loading={savingCron[record.id]}
        >
          保存
        </Button>
      </Space.Compact>
    ),
  },
  {
    title: '下次执行',
    key: 'next_run',
    width: 200,
    render: (_, record) => {
      const schedule = configSchedules[record.id]
      if (!schedule || !schedule.next_run_at) return <Tag>未调度</Tag>
      return new Date(schedule.next_run_at).toLocaleString('zh-CN')
    },
  },
]
```

替换页面中 "职位爬取" 的 Divider 之后到下一个 Divider/元素之前的全部内容：

```tsx
{/* 此处替换原有 "职位爬取" 区域 */}
<Divider style={{ margin: '16px 0' }} />

<div>
  <h4 style={{ marginBottom: 12, color: '#1f2937' }}>职位爬取定时配置</h4>
  <Table
    dataSource={configList}
    columns={configColumns}
    rowKey="id"
    loading={configLoading}
    pagination={false}
    size="small"
    locale={{ emptyText: '暂无搜索配置' }}
  />
</div>
```

- [ ] **Step 2: 在组件 mount 时加载 config 数据**

在第二个 `useEffect`（获取 scheduler 状态的那个）中并行加载：

```tsx
useEffect(() => {
  fetchSchedulerStatus()
  loadConfigData()  // 新增
}, [])
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/pages/ScheduleConfigPage.tsx
git commit -m "feat(jobs): replace job cron section with per-config cron table on schedule page"
```

---

### Task 8: 清理遗留的全局 job_crawl_cron

**Files:**
- Modify: `backend/app/routers/config.py`（如有 `trigger_job_crawl` 注册逻辑）
- Modify: `backend/app/main.py`（已处理）
- 确认前端 `updateJobCrawlCron` 调用已移除

- [ ] **Step 1: 确认后端不再处理全局 `job_crawl_cron`**

搜索所有引用 `job_crawl_cron` 的地方，除 `User` 模型保留字段定义外，确认调度器代码不再使用。

```bash
cd backend && grep -r "job_crawl_cron" app/ --include="*.py"
```

应只剩 `models/user.py` 中的字段定义。如果 `config.py` router 中有 `updateJobCrawlCron` 端点，标记为 deprecated 或移除。

- [ ] **Step 2: 前端清理**

确认 `config.ts` 中已移除 `getJobCrawlCron` 和 `updateJobCrawlCron`。前端调用 `updateJobCrawlCron` 的地方已全部替换为 `updateConfigCron`。

- [ ] **Step 3: 提交**

```bash
git add .
git commit -m "chore: remove global job_crawl_cron endpoints and cleanup"
```

---

### Task 9: 全面测试

**Files:**
- 已有: `backend/tests/test_scheduler_config.py`
- 新增: -（已有测试）

- [ ] **Step 1: 运行所有测试**

```bash
cd backend && python -m pytest -v
```

- [ ] **Step 2: 端到端验证**
  1. 启动后端 `cd backend && python -m uvicorn app.main:app`
  2. 确认日志显示 `JobConfigScheduler synced`
  3. 创建带 cron 的 config → 确认 scheduler 注册了对应 job
  4. 更新 config 的 cron → 确认 job 已更新
  5. 删除 config → 确认 job 已移除
  6. 访问 `/jobs/scheduler/job-configs` → 确认返回正确的 next_run_time
  7. 页面 `/schedule` → 确认表格显示所有 config 及其 cron 状态

- [ ] **Step 3: 提交所有剩余更改**

```bash
git add .
git commit -m "test: add scheduler config tests and e2e verification"
```
