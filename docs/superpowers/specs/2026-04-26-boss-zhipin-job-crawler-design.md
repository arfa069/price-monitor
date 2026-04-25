# Boss直聘职位爬取系统设计

## 概述

在现有价格监控系统的基础上，新增 boss 直聘职位搜索爬取功能。复用 CDP 模式连接已登录浏览器，批量抓取搜索列表页职位数据，去重存储并支持新职位飞书通知。

## 目标

- 从 boss 直聘搜索列表页批量抓取职位信息
- 配置化管理搜索条件，APScheduler 定时自动爬取
- 用 `job_id`（encryptJobId）去重，记录首次发现和最后更新时间
- 新职位发现时通过飞书 Webhook 发送通知

## 架构方案

选择**方案 A：扩展适配器模式**。在现有平台适配器体系中新增 `BossZhipinAdapter`，扩展 `BasePlatformAdapter` 的浏览器生命周期，复用 CDP 连接、APScheduler 调度器和 CrawlLog 日志体系。新增代码集中在独立模块，不破坏现有价格监控代码。

---

## 第一章：数据模型

### JobSearchConfig（搜索配置）

用户配置一组搜索条件，调度器按配置的 URL 定时爬取。

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | PK | |
| `user_id` | FK → users.id | 硬编码为 1 |
| `name` | String(100) | 配置名称，如"北京 Python 职位" |
| `keyword` | String(200) | 搜索关键词 |
| `city_code` | String(20) | boss 直聘城市代码，可选 |
| `salary_min` / `salary_max` | Integer | 薪资范围（单位 K），可选 |
| `experience` | String(50) | 经验要求，如"1-3年"，可选 |
| `education` | String(50) | 学历要求，如"本科"，可选 |
| `url` | Text | **完整的搜索 URL**，可直接用于 Playwright 访问 |
| `active` | Boolean | 是否启用定时爬取，默认 True |
| `notify_on_new` | Boolean | 新职位是否发送飞书通知，默认 True |

`url` 是核心字段。用户在前端配置条件后，系统拼接成 boss 直聘的搜索 URL 存入。爬取时直接访问该 URL，不依赖字段重新拼接。

### Job（职位数据）

每个爬取到的职位一条记录，用 `job_id`（boss 直聘的 `encryptJobId`）去重。

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | PK | |
| `job_id` | String(100), unique, index | boss 直聘的 encryptJobId |
| `search_config_id` | FK → job_search_configs.id | 来源搜索配置 |
| `title` | String(300) | 职位名称 |
| `company` | String(200) | 公司名称 |
| `company_id` | String(100) | boss 直聘公司 ID，可选 |
| `salary` | String(100) | 原始薪资字符串，如"20-40K·14薪" |
| `salary_min` / `salary_max` | Integer | 解析后的数值（单位 K） |
| `location` | String(200) | 工作地点 |
| `experience` | String(100) | 经验要求 |
| `education` | String(100) | 学历要求 |
| `description` | Text | 职位描述，截取前 500 字符 |
| `url` | Text | 职位详情页 URL |
| `first_seen_at` | DateTime(tz=True) | 首次发现时间 |
| `last_updated_at` | DateTime(tz=True) | 最后更新时间 |
| `is_active` | Boolean, default=True | 是否仍在招聘 |

关系：`JobSearchConfig` 1:N `Job`（通过 `search_config_id`）。

### CrawlLog 扩展复用

现有 `CrawlLog` 的 `platform` 字段扩展为包含 `'boss'`。语义映射：

| CrawlLog 字段 | 价格监控 | 职位爬取 |
|---------------|----------|----------|
| `product_id` | `Product.id` | `JobSearchConfig.id` |
| `platform` | `'taobao'` / `'jd'` / `'amazon'` | `'boss'` |
| `status` | `SUCCESS` / `ERROR` | `SUCCESS` / `ERROR` |
| `price` | 商品价格 | 本次发现的新职位数量 |
| `currency` | `CNY` / `USD` | `None` |
| `error_message` | 错误信息 | 错误信息 |

### User 模型扩展

`User` 模型新增 `job_crawl_cron` 字段（与现有 `crawl_cron` 独立），允许独立配置职位爬取的定时频率。

---

## 第二章：适配器与爬取流程

### BossZhipinAdapter 设计

`BossZhipinAdapter` 继承 `BasePlatformAdapter`，**重写 `crawl()` 方法**，但复用底层的 CDP 浏览器生命周期（`_init_browser()` / `_close_browser()`）。

`BasePlatformAdapter` 的 `extract_price()` 和 `extract_title()` 为抽象方法，BossZhipinAdapter 空实现并抛异常——boss 平台不走单商品价格提取路径。

### 核心流程

```
crawl(url)
    ↓
_init_browser()          ← 复用 BasePlatformAdapter CDP 连接
    ↓
goto(url, wait_until=domcontentloaded)
    ↓
wait_for_selector(".job-card-wrapper", timeout=20s)
    ↓
_scroll_to_load_more()   ← 最多 5 次滚动，每次等 1.5s
    ↓
page.evaluate 内联 JS    ← 一次性提取所有职位卡片
    ↓
_close_browser()         ← 仅关闭 page，复用 browser 实例
    ↓
返回 {"success": true, "jobs": [...], "count": N}
```

### 滚动加载策略

Boss 直聘列表页为无限滚动，每页约 30 条。滚动策略：

- 最多滚动 5 次，预计覆盖 150 条职位
- 每次滚动后等待 1.5s 让新卡片渲染
- 若滚动前后职位数量不变，提前终止

### 提取策略

使用 `page.evaluate` 内联 JavaScript 一次性提取所有卡片，比逐个 `locator` 快一个数量级。提取字段：

- `job_id`：从卡片 `data-jobid` 属性获取
- `title`：`.job-name` 元素
- `company`：`.company-name` 元素
- `salary`：`.salary` 元素
- `location`：`.job-area` 元素
- `experience`、`education`：`.tag-list li` 前两个
- `url`：卡片内 `<a>` 链接

### CDP 模式要求

Boss 直聘反爬严格，CDP 复用已登录浏览器是必须条件。需要用户先在浏览器中登录 boss 直聘，再以 `--remote-debugging-port=9222` 启动，配置 `CDP_ENABLED=true`。

---

## 第三章：API 路由与调度器集成

### /jobs 路由端点

```python
router = APIRouter(prefix="/jobs", tags=["jobs"])
```

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/jobs/configs` | 获取所有搜索配置列表 |
| `POST` | `/jobs/configs` | 创建搜索配置 |
| `GET` | `/jobs/configs/{id}` | 获取单个配置详情 |
| `PUT` | `/jobs/configs/{id}` | 更新配置 |
| `DELETE` | `/jobs/configs/{id}` | 删除配置（级联删除关联 Job） |
| `GET` | `/jobs` | 获取职位列表（分页 + 筛选） |
| `GET` | `/jobs/{job_id}` | 获取单个职位详情 |
| `POST` | `/jobs/crawl-now` | 手动触发所有活跃配置的爬取 |
| `POST` | `/jobs/crawl-now/{config_id}` | 手动触发单个配置的爬取 |
| `GET` | `/jobs/status/{task_id}` | 获取爬取任务状态（复用 CrawlTask 体系） |

### 职位列表筛选（GET /jobs）

支持查询参数：

| 参数 | 类型 | 说明 |
|------|------|------|
| `search_config_id` | int | 按来源配置筛选 |
| `keyword` | str | 关键词搜索（title、company、description 模糊匹配） |
| `company` | str | 公司名筛选 |
| `salary_min` | int | 最低薪资（K） |
| `salary_max` | int | 最高薪资（K） |
| `location` | str | 工作地点 |
| `is_active` | bool | 是否仍在招聘 |
| `sort_by` | str | `first_seen_at` \| `last_updated_at` \| `salary_min` |
| `sort_order` | str | `desc` \| `asc` |
| `page` | int | 页码，默认 1 |
| `page_size` | int | 每页条数，默认 20，最大 100 |

### 调度器集成

复用现有 APScheduler，在 `_start_scheduler()` 中新增定时任务：

```python
# 职位爬取定时任务
scheduler.add_job(
    _trigger_crawl_jobs,
    trigger=CronTrigger.from_crontab(user.job_crawl_cron or "0 9 * * *", timezone=tz),
    id="job_crawl_cron_job",
    name="Crawl all active job searches",
    replace_existing=True,
)
```

与现有价格监控共享同一个 APScheduler 实例，但使用独立的 cron 配置（`User.job_crawl_cron`），支持不同频率。

### 与现有价格监控的关系

| 维度 | 价格监控 | 职位爬取 |
|------|----------|----------|
| 调度器 | 同一个 APScheduler | 同一个 APScheduler |
| 定时配置 | `User.crawl_cron` | `User.job_crawl_cron` |
| 爬取任务 | `_trigger_crawl_all` | `_trigger_crawl_jobs` |
| 状态跟踪 | 复用 CrawlTask | 复用 CrawlTask |
| 通知渠道 | 飞书 Webhook | 飞书 Webhook |

---

## 第四章：去重、变化检测与通知

### 去重逻辑

核心函数 `process_job_results(config_id, jobs)`：

```
对每个爬取到的职位：
    用 job_id 查询 Job 表
    ├── 存在 → 更新 last_updated_at，标记 is_active=True
    └── 不存在 → 插入新记录，标记 first_seen_at 和 last_updated_at

本次所有处理完后：
    将上一次爬取结果中存在但本次未出现的职位标记为 is_active=False
```

### V1 简化策略

| 场景 | V1 行为 |
|------|---------|
| 新职位 | 插入数据库 + 可选飞书通知 |
| 已存在且仍在列表中 | 更新 `last_updated_at`，标记 `is_active=True` |
| 已存在但不在本次结果中 | 标记 `is_active=False`（职位已下架） |

V1 **不追踪已有职位的信息变化**（如薪资从 20K 调到 25K），只标记"发现"和"下架"。变化追踪需要变更历史表，留到 V2。

### 飞书通知

`JobSearchConfig.notify_on_new` 字段控制是否发送通知。

通知内容示例：

```
🔔 Boss直聘新职位提醒

搜索配置：北京 Python 后端
本次发现 3 个新职位（共扫描 42 个）：

1. Python后端开发工程师
   字节跳动 · 北京·海淀区
   💰 30-50K·16薪  |  3-5年  |  本科
   🔗 https://www.zhipin.com/job_detail/xxx

2. 高级Python工程师
   美团 · 北京·朝阳区
   💰 35-60K·15薪  |  5-10年  |  本科
   🔗 ...

...

---
共收录 156 个职位 | 查看全部：http://localhost:5173/jobs
```

### 薪资解析

从原始薪资字符串（如"20-40K·14薪"）解析出 `salary_min` 和 `salary_max`（单位 K）：

- 提取薪资范围的最小值和最大值
- 统一换算为"K"单位（如"20-40K" → min=20, max=40）
- 特殊格式如"面议"解析为 null

---

## 文件结构

```
app/
├── models/
│   ├── job.py              # JobSearchConfig, Job 模型
│   └── user.py             # User 模型扩展 job_crawl_cron
├── platforms/
│   └── boss.py             # BossZhipinAdapter
├── services/
│   ├── job_crawl.py        # process_job_results, crawl_all_job_searches
│   └── notification.py     # send_new_job_notification 扩展
├── routers/
│   └── jobs.py             # /jobs 路由
├── schemas/
│   └── job.py              # Pydantic schemas
└── main.py                 # 调度器新增 job_crawl_cron 任务

alembic/versions/
└── xxx_add_job_tables.py    # 迁移文件

docs/superpowers/specs/
└── 2026-04-26-boss-zhipin-job-crawler-design.md
```

---

## 验收标准

1. **CDP 连接**：配置 `CDP_ENABLED=true` 后，boss 直聘登录态被复用
2. **职位提取**：从搜索列表页能正确提取 job_id、title、company、salary、location 等字段
3. **滚动加载**：5 次滚动后能覆盖约 100+ 职位
4. **去重**：重复爬取不会创建重复 Job 记录
5. **下架检测**：上一次存在但本次不在列表中的职位被标记为 `is_active=False`
6. **飞书通知**：新职位被发现时能发送带职位详情的通知
7. **定时调度**：`User.job_crawl_cron` 能独立控制职位爬取频率
8. **API 可用**：`/jobs` 和 `/jobs/configs` 端点正常响应

---

## 未来扩展

- V2：职位信息变化追踪（薪资、JD 变更历史）
- V2：职位详情页爬取（完整 JD 内容）
- V2：职位相似推荐（基于关键词和公司）
