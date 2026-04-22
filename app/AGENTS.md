# app/ — 主应用

核心应用代码：模型、API 路由、平台爬虫、Celery 任务、服务。

## 子目录

| 子目录 | 用途 |
|--------|------|
| `models/` | SQLAlchemy 模型（user, product, price_history, alert, crawl_log） |
| `platforms/` | 淘宝、京东、亚马逊爬虫（Playwright，防爬措施） |
| `routers/` | API 端点（config, products, alerts, crawl） |
| `schemas/` | Pydantic 请求/响应 schema |
| `services/` | 通知服务（飞书 Webhook） |
| `tasks/` | Celery 任务（抓取产品、清理旧记录） |

## 关键文件

| 文件 | 用途 |
|------|------|
| `main.py` | FastAPI 应用工厂 + 生命周期 |
| `config.py` | Pydantic BaseSettings（数据库 URL、Redis、飞书、平台凭证） |
| `database.py` | 异步引擎、会话工厂、`get_db()` 依赖注入 |
| `celery_app.py` | Celery 配置（broker=Redis，backend=Redis） |

## 模式

- **数据库**：`async for` + `async_session.begin()` — 禁止使用 `session.execute()`
- **平台爬虫**：`BasePlatform` ABC，`crawl()` → `ProductSnapshot`
- **Celery 任务**： `@celery_app.celery_app.task`，位于 `tasks/crawl.py`
- **路由**：FastAPI `APIRouter`，前缀 `/api/v1`
- **Schema**：所有请求/响应使用 `schemas/` 中的 Pydantic 模型

## 平台适配器契约

所有平台爬虫继承 `BasePlatform`，必须实现：

```python
def crawl(self, url: str) -> ProductSnapshot: ...
async def is_available(self) -> bool: ...
```

`ProductSnapshot` 字段：`platform`, `product_id`, `title`, `price`, `original_price`, `stock_status`, `crawled_at`