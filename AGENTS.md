# Price Monitor

淘宝、京东、亚马逊电商价格监控系统，支持降价提醒。

## 项目概览

**类型**：Python 3.11+ FastAPI 应用
**技术栈**：FastAPI · 异步 SQLAlchemy · PostgreSQL · Redis/Celery · Playwright · 飞书 Webhook
**入口**：`app/main.py`

## 命令

```powershell
# 运行
uvicorn app.main:app --reload

# 测试
pytest

# 检查
ruff check .
```

## 关键文件

| 文件 | 用途 |
|------|------|
| `app/main.py` | FastAPI 入口，应用工厂 |
| `app/config.py` | Pydantic 配置（数据库、Redis、飞书、平台凭证） |
| `app/database.py` | 异步 SQLAlchemy 引擎与会话 |
| `app/celery_app.py` | Celery 配置 |
| `app/platforms/` | 淘宝、京东、亚马逊爬虫（Playwright，防爬措施） |
| `app/models/` | SQLAlchemy 模型（user, product, price_history, alert, crawl_log） |
| `app/routers/` | API 端点（config, products, alerts, crawl） |
| `app/tasks/` | Celery 任务（抓取产品、清理旧记录） |

## 架构

- **平台适配器**：`app/platforms/base.py`（ABC）→ `amazon.py`, `jd.py`, `taobao.py`
- **爬虫**：Playwright 处理 JS 渲染页面；Celery worker 异步调度
- **告警**：检测到降价 → 飞书 Webhook 通知
- **数据库迁移**：Alembic + 异步 SQLAlchemy

## 模式

- 所有数据库操作用 `async for` + `async_session.begin()`
- 平台爬虫实现 `BasePlatform.crawl()` → 返回 `ProductSnapshot`
- Celery 任务在 `app/tasks/crawl.py`，通过 `celery_app.celery_app` 调度