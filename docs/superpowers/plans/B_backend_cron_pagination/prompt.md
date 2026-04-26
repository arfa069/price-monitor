# 提示词B（V3）：阶段2 - 后端 Cron 调度 + Products 分页 + 前端联动

你是资深全栈工程师。请在现有 FastAPI + React 项目中完成第二阶段开发：
1) 后端支持可配置 Cron 自动爬取（APScheduler，Asia/Shanghai）
2) 后端为 products 提供分页查询
3) 前端“定时配置页”改为真实读写 /config，localStorage 仅草稿兜底
4) 前端“商品管理页”改为服务端分页，每页 15 条

一、后端配置与数据模型
- 在 users 配置中新增字段：
  - crawl_cron: string，默认 "0 * * * *"
  - crawl_timezone: string，默认 "Asia/Shanghai"
- 更新 SQLAlchemy model、Pydantic schema、Alembic migration
- /config 接口：
  - GET /config 返回 crawl_cron、crawl_timezone
  - POST /config 保持可用（全量 upsert）
  - PATCH /config 新增，支持部分更新（至少支持单独改 crawl_cron）
- 校验：
  - crawl_cron 使用标准 5 段 crontab
  - crawl_timezone 至少支持 Asia/Shanghai（无效时返回 422）

二、后端调度器（APScheduler）
- 使用 AsyncIOScheduler，在 FastAPI lifespan 启动时初始化
- 启动时读取 user_id=1 配置并注册定时任务
- 定时任务直接调用内部 crawl 逻辑，不通过 HTTP 自调用
- 当 POST/PATCH /config 更新 crawl_cron 时，立即重建并热更新 job
- 固定 job_id，防重复注册
- 并发保护：若上一次抓取未完成，本次触发跳过并记录日志
- 关闭应用时优雅 shutdown scheduler

三、后端 products 分页
- 在 GET /products 中支持服务端分页参数：
  - page: 默认 1，>=1
  - page_size: 默认 15，范围 1~100
  - platform/active/keyword 筛选继续支持
- 返回分页结构：
  - items, total, page, page_size, total_pages, has_next, has_prev
- 排序：created_at desc, id desc（稳定排序）

四、前端联动改造
- 商品管理页改为服务端分页，固定每页 15 条
- 翻页、筛选、关键词搜索都走后端查询参数
- 定时配置页：
  - 页面加载先 GET /config 展示真实值
  - 用户编辑但未保存时，写入 localStorage 草稿
  - 保存时调用 PATCH /config
  - 保存成功后清空草稿并同步页面状态
  - 保存失败时保留草稿并提示可重试
- 若检测到“本地草稿 != 后端值”，展示“恢复草稿/丢弃草稿”选择

五、必须覆盖的边界场景
- 配置不存在时：自动创建默认配置或返回可引导的默认值
- 非法 cron 返回 422，错误信息可读
- 更新 cron 与任务执行同时发生时：当前执行可完成，新配置从下一次触发生效
- page 超出范围：返回空 items + 正常分页元信息，不抛 500
- 筛选无结果：返回空列表并正常 total=0
- 批量删除后当前页为空：前端自动回退到上一页并刷新
- 数据库/Redis 短时异常：接口返回明确错误，前端可重试提示
- 避免日志静默失败：调度更新、跳过执行、执行异常都记录结构化日志

六、测试与文档
- 测试新增/更新：
  - /config PATCH 更新 crawl_cron 成功
  - 非法 crawl_cron 返回 422
  - scheduler job 在配置更新后被替换
  - /products 分页、筛选、越界页行为正确
- 更新 README.md 与 ARCHITECTURE.md：
  - 新增 cron 配置说明
  - 新增 products 分页接口说明
  - 说明前端定时配置页已对接真实后端，localStorage 为草稿兜底

请输出完整代码改动、迁移步骤、测试命令与关键结果。

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 1 | clean | HOLD scope, 2 expansions accepted |
| Codex Review | `/codex review` | Independent 2nd opinion | 0 | — | — |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | issues_open | 8 issues, 2 critical gaps |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | — | — |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | — | — |

**CROSS-MODEL:** Outside voice (eng-review subagent) found 10 structural issues. All 11 decisions from eng-review resolved. CEO review added 2 scope expansions: 调度失败飞书通知 + GET /scheduler/status 端点。

**UNRESOLVED:** 0

**VERDICT:** CEO + ENG CLEARED — ready to implement

### CEO Review additions
- 调度任务失败 → 写 CrawlLog + 飞书通知（scope expansion）
- 新增 `GET /scheduler/status` 端点（scope expansion）
- APScheduler job 需设置 `max_instances=1` 防内存泄漏

### Decisions resolved during review (all sections)
1. user_id=1 不存在时 → 跳过调度注册，记日志
2. Cron 并发保护 → asyncio.Event + 标志位
3. Crawl 逻辑组织 → 提取 crawl_all_active_products() 内部函数
4. Products 排序 → created_at desc + id desc
5. 前端草稿竞态 → 等 GET /config 完成再弹恢复选择
6. 测试策略 → 完整 API + E2E
7. APScheduler → 3.x (not 4.x beta)
8. 频率策略 → crawl_cron 与 crawl_frequency_hours 互斥，Radio 切换
9. 全局并发锁 → asyncio.Semaphore(1) 覆盖 cron + crawl-now
10. 前端表单 → 保留两个表单，Radio 切换模式
11. PATCH bug → 修复 create-if-not-exists 分支的 exclude_unset 问题
12. 调度失败可见性 → CrawlLog + 飞书通知
13. 调度器状态 → GET /scheduler/status 端点

### NOT in scope
- Cron 执行历史记录查询 API（可通过 crawl_logs + source 字段后续实现）
- 多用户支持
- 批量操作的分页保持优化

### Dream state delta
Current: manual crawl only → This plan: scheduled cron + config + pagination → 12-month ideal: multi-user, success-rate dashboard, failure alerts, price prediction. Gap: observability dashboard + price history analytics.

### Parallelization
Lane A: User model + schema + migration → Lane B: Products pagination → Lane C: APScheduler + scheduler endpoint → Lane D+E: Frontend changes (parallel) → Lane F: Tests

