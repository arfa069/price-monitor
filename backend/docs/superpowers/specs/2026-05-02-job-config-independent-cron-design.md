# JobSearchConfig 独立 Cron 定时器设计

> **状态:** 已批准
> **日期:** 2026-05-02

## 目标

每个 `JobSearchConfig` 可以独立设置自己的 cron 定时表达式，实现各自的定时爬取，互不干扰。

## 设计决策

- 取消全局 `User.job_crawl_cron` 调度，改为每个 config 独立调度
- config 没有设 cron 就不定时，没有兜底回退
- 使用 `SchedulerManager` 封装 APScheduler job 的增删改逻辑，方案 A（CRUD 时同步）
- 前端在 `/schedule` 页面统一管理所有 config 的 cron 设置
- `User.job_crawl_cron` 字段保留不动（兼容已有数据，不再被调度器使用）

## 数据库变更

### JobSearchConfig 表追加字段

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `cron_expression` | `String(100)` | nullable=True | 5段 crontab 表达式，null 表示不定时 |
| `cron_timezone` | `String(50)` | nullable=True, default="Asia/Shanghai" | 时区 |

需要新增 Alembic 迁移文件。

## 后端调度器

### SchedulerManager 类

封装 APScheduler 操作，方法：

- `__init__(scheduler: AsyncIOScheduler)` — 持有 scheduler 引用
- `sync_all()` — 启动时遍历 DB 中 `cron_expression IS NOT NULL` 的 config，逐个注册 job
- `add_job(config_id, cron_expression, timezone)` — 注册或替换单个 config 的 job
- `remove_job(config_id)` — 移除 config 的 job

Job ID 规范：`job_config_cron_{config_id}`

每个 job 触发时调用 `crawl_single_config(config_id)`，不再调用 `crawl_all_job_searches`。

### main.py 启动流程调整

1. 现有产品 cron 注册逻辑不变
2. 创建 `SchedulerManager` 实例，挂到 `app.state`
3. 调用 `scheduler_manager.sync_all()`
4. 不再注册全局 `job_crawl_cron_job`

## API 变更

### Config CRUD 端点

- `POST /jobs/configs` — 创建后，若 `cron_expression` 非空则调用 `scheduler_manager.add_job()`
- `PATCH /jobs/configs/{id}` — 更新后同步 scheduler（cron 变更或清空）
- `DELETE /jobs/configs/{id}` — 删除前调用 `scheduler_manager.remove_job()`

### 新增端点

- `PATCH /jobs/configs/{id}/cron` — 只更新 `cron_expression` 和 `cron_timezone`，专供 /schedule 页面使用
  - 请求体: `{ "cron_expression": "0 9 * * *" | null, "cron_timezone": "Asia/Shanghai" }`
  - 后端同时同步 scheduler

### 开机恢复

停机重启时 APScheduler 不持久化 job。`sync_all()` 在启动时从 DB 重建所有 job，天然恢复。

## 前端变更

### /schedule 页面

将当前"职位爬取"Cron 区替换为 config 级配置表格：

1. 从 `GET /jobs/configs` 获取所有 config 列表
2. 每行显示：config 名称、Cron 输入框、保存按钮、清除按钮
3. 保存时调用 `PATCH /jobs/configs/{id}/cron`
4. 清除时设置 `cron_expression = null`
5. 表格下方显示下次执行时间（需新增 `GET /jobs/configs/cron/next-run` 或以在 config 列表响应中附加 scheduler 信息）

### 下次执行时间

新增 `GET /scheduler/job-configs` 端点，返回所有有 cron 的 config 的 next_run_time：

```json
{
  "configs": [
    { "config_id": 1, "cron_expression": "0 9 * * *", "next_run_at": "2026-05-03T01:00:00+08:00" },
    { "config_id": 2, "cron_expression": "0 18 * * *", "next_run_at": "2026-05-02T10:00:00+08:00" }
  ]
}
```

## 错误处理

- CRUD 操作成功但 scheduler 调用失败：记录日志，不影响 API 响应（配置已写入 DB，重启后自动恢复）
- crontab 表达式校验：后端 Pydantic schema 做格式校验，前端也做客户端校验
- 无效时区：回退到 `"Asia/Shanghai"`，记录警告日志

## 测试要点

- 启动时 `sync_all()` 正确注册所有有 cron 的 config
- CRUD 创建/更新/删除时 scheduler 同步
- 无效 cron 表达式被拒绝
- 停机重启后恢复所有定时 job
