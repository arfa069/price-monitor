# CLAUDE.md

此文件为 Claude Code (claude.ai/code) 提供代码库操作指南。

## 项目概览

淘宝、京东、亚马逊价格监控系统。通过 Playwright 抓取商品页面，记录价格历史，降价时通过飞书 Webhook 发送通知。

**技术栈**：Python 3.11+ · FastAPI · PostgreSQL (async SQLAlchemy) · Redis · Playwright · 飞书 Webhook

## 常用命令

```powershell
# 安装依赖
pip install -e .

# 运行数据库迁移
alembic upgrade head

# 启动开发服务器
uvicorn app.main:app --reload

# 运行测试
pytest

# 代码检查
ruff check .

# Docker Compose 完整启动
docker-compose up -d
```

## 架构

### 入口文件
- `app/main.py` — FastAPI 应用工厂，含 lifespan、路由注册、/health 检查
- `app/config.py` — Pydantic Settings，环境变量

### 平台适配器模式
```
app/platforms/base.py     — BasePlatformAdapter (ABC)：_init_browser、crawl、extract_price/title（抽象方法）
app/platforms/taobao.py   — TaobaoAdapter
app/platforms/jd.py       — JDAdapter
app/platforms/amazon.py  — AmazonAdapter
```
每个适配器实现 `extract_price()` 和 `extract_title()`。基类负责 Playwright 生命周期管理（每次抓取 90s 超时，支持代理/CDP 模式）。

### 数据库模式
所有数据库操作用 `async with AsyncSessionLocal() as db:` 配合 `await db.commit()`。
- `app/database.py` — 异步引擎、AsyncSessionLocal、get_db 依赖注入
- `app/models/` — SQLAlchemy 模型：User、Product、PriceHistory、Alert、CrawlLog
- `alembic/versions/` — 迁移文件

### 抓取流程（`POST /crawl/crawl-now`）
- `_crawl_one()` 在 FastAPI async 上下文中直接运行，无 Celery 依赖
- `check_price_alerts()` 在每次抓取后对比最近两条价格记录，跌幅达标则发飞书通知
- `POST /crawl/cleanup` 手动触发旧数据清理

### CDP 模式
连接已登录浏览器（`--remote-debugging-port=9222`），复用登录态绕过反爬：
```
CDP_ENABLED=true
CDP_URL=http://127.0.0.1:9222
```

## 关键约束
- user_id 硬编码为 1（单用户系统）
- 所有时间戳字段使用 UTC 时区（`datetime.now(timezone.utc)`）
- 价格比较使用 Decimal 避免浮点误差
