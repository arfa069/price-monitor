# Price Monitor

淘宝、京东、亚马逊电商价格监控系统，支持降价提醒与飞书通知。

## 项目概览

- 类型：Python 3.11+ FastAPI 应用
- 技术栈：FastAPI · 异步 SQLAlchemy · PostgreSQL · Redis · Playwright · 飞书 Webhook
- 入口：`app/main.py`
- 架构基线：抓取任务在 FastAPI 异步上下文内执行，不依赖 Celery worker

## 常用命令

```powershell
# 启动服务（Windows 建议不要加 --reload）
uvicorn app.main:app

# 迁移
alembic upgrade head

# 测试
pytest

# 代码检查
ruff check .
```

## 关键能力

- 多平台价格采集：淘宝 / 京东 / 亚马逊
- CDP 模式：复用已登录浏览器会话，降低反爬与登录墙影响
- 降价告警：基于价格历史比较并通过飞书 webhook 推送
- 数据清理：支持按保留天数清理历史价格和抓取日志

## 关键文件

| 文件 | 用途 |
|------|------|
| `app/main.py` | FastAPI 入口与生命周期管理 |
| `app/config.py` | Pydantic Settings（数据库、Redis、飞书、CDP/代理配置） |
| `app/database.py` | 异步 SQLAlchemy 引擎与会话 |
| `app/platforms/base.py` | 平台适配器抽象基类 |
| `app/routers/crawl.py` | 抓取、日志查询、数据清理接口 |
| `app/services/crawl.py` | 抓取编排与告警触发逻辑 |
| `app/services/notification.py` | 飞书通知发送 |

## 架构要点

- 平台适配器模式：`BasePlatformAdapter` -> `taobao.py` / `jd.py` / `amazon.py`
- 浏览器模式：Launch（默认）与 CDP（连接 `--remote-debugging-port=9222`）
- 抓取策略：`domcontentloaded` + 价格选择器等待 + 随机延时，单次抓取超时 90s
- API 入口：`/config`、`/products`、`/alerts`、`/crawl/*`、`/health`

## 与文档保持一致

更新本文件时，以 `README.md` 与 `ARCHITECTURE.md` 为准；若实现与文档冲突，优先修正文档并在 PR 中说明。
