# app/ — 主应用

核心应用代码目录：API、平台适配器、抓取服务、通知服务、模型与 schema。

## 子目录

| 子目录 | 用途 |
|--------|------|
| `models/` | SQLAlchemy 模型（user, product, price_history, alert, crawl_log） |
| `platforms/` | 平台适配器（淘宝、京东、亚马逊） |
| `routers/` | FastAPI 路由（config, products, alerts, crawl） |
| `schemas/` | Pydantic 请求/响应模型 |
| `services/` | 抓取编排与通知服务 |
| `api/` | 预留 API 模块 |
| `crawlers/` | 预留抓取相关模块 |

## 关键文件

| 文件 | 用途 |
|------|------|
| `main.py` | FastAPI 应用创建与生命周期管理 |
| `config.py` | 配置加载（DATABASE_URL、REDIS_URL、FEISHU、CDP、代理等） |
| `database.py` | 异步数据库引擎、会话工厂、`get_db()` |
| `routers/crawl.py` | 手动触发抓取、查询抓取日志、触发清理 |
| `services/crawl.py` | 抓取执行、价格落库、告警判断 |
| `services/notification.py` | 飞书 webhook 发送与重试 |
| `platforms/base.py` | `BasePlatformAdapter` 抽象与浏览器初始化 |

## 实现模式

- 数据库：统一使用异步 SQLAlchemy 会话与事务。
- 抓取：在 FastAPI 异步上下文内顺序处理活动商品，不走 Celery。
- 平台扩展：新增平台时实现适配器并接入统一抓取编排。
- 浏览器：支持 Launch 与 CDP 两种模式；CDP 用于复用登录态与降低反爬影响。

## 开发注意

- Windows 下运行 `uvicorn app.main:app`，不要加 `--reload`（Playwright 子进程不稳定）。
- 页面等待策略优先 `domcontentloaded`，再等待价格选择器，避免 `networkidle` 卡住。
- 价格与告警逻辑改动需同步更新对应路由和测试。
