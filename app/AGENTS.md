# app/ — 主应用

核心应用代码：模型、API 路由、平台爬虫、服务。

## 子目录

| 子目录 | 用途 |
|--------|------|
| `models/` | SQLAlchemy 模型（user, product, price_history, alert, crawl_log） |
| `platforms/` | 淘宝、京东、亚马逊爬虫（Playwright，防爬措施） |
| `routers/` | API 端点（config, products, alerts, crawl） |
| `schemas/` | Pydantic 请求/响应 schema |
| `services/` | 通知服务（飞书 Webhook）、抓取服务（爬取/告警逻辑） |

## 关键文件

| 文件 | 用途 |
|------|------|
| `main.py` | FastAPI 应用工厂 + 生命周期 |
| `config.py` | Pydantic BaseSettings（数据库 URL、Redis、飞书、平台凭证） |
| `database.py` | 异步引擎、会话工厂、`get_db()` 依赖注入 |

## 模式

- **数据库**：`async with AsyncSessionLocal() as db:` + `await db.commit()`
- **平台爬虫**：`BasePlatformAdapter` ABC，`crawl()` 返回 `{success, price, currency, title}`
- **抓取逻辑**：`app/routers/crawl.py` 的 `_crawl_one()` 直接运行于 FastAPI async 上下文，无 Celery
- **路由**：FastAPI `APIRouter`
- **Schema**：所有请求/响应使用 `schemas/` 中的 Pydantic 模型
