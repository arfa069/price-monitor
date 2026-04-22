# CLAUDE.md

此文件为 Claude Code (claude.ai/code) 提供代码库操作指南。

## 项目概览

淘宝、京东、亚马逊价格监控系统。通过 Playwright 抓取商品页面，记录价格历史，降价时通过飞书 Webhook 发送通知。

**技术栈**：Python 3.11+ · FastAPI · PostgreSQL (async SQLAlchemy) · Redis + Celery · Playwright · 飞书 Webhook

## 常用命令

```powershell
# 安装依赖
pip install -e .

# 运行数据库迁移
alembic upgrade head

# 启动开发服务器（自动重载）
uvicorn app.main:app --reload

# 运行测试
pytest

# 运行单个测试文件
pytest tests/test_api.py

# 代码检查
ruff check .

# Docker Compose 完整启动
docker-compose up -d
```

## 架构

### 入口文件
- `app/main.py` — FastAPI 应用工厂，含 lifespan、路由注册、/health 检查
- `app/celery_app.py` — Celery 配置，beat 调度（定期抓取 + 每日清理）
- `app/config.py` — Pydantic Settings，环境变量，`redis_url_with_password` 属性

### 平台适配器模式
```
app/platforms/base.py     — BasePlatformAdapter (ABC)：_init_browser、crawl、extract_price/title（抽象方法）
app/platforms/taobao.py   — TaobaoAdapter
app/platforms/jd.py       — JDAdapter
app/platforms/amazon.py  — AmazonAdapter
```
每个适配器实现 `extract_price()` 和 `extract_title()`。基类负责 Playwright 生命周期管理（每次抓取 60s 超时，支持代理）。

### 数据库模式
所有数据库操作用 `async with AsyncSessionLocal() as db:` 配合 `await db.commit()`。
- `app/database.py` — 异步引擎、AsyncSessionLocal、get_db 依赖注入
- `app/models/` — SQLAlchemy 模型：User、Product、PriceHistory、Alert、CrawlLog
- `alembic/versions/` — 迁移文件

### Celery 任务模式
`app/tasks/crawl.py` 中的任务使用 `shared_task(bind=True)` 包装异步函数：
```python
@shared_task(bind=True, max_retries=3)
def crawl_product(self, product_id: int) -> dict:
    loop = asyncio.get_event_loop()
    async def _crawl():
        # 异步代码
    return loop.run_until_complete(_crawl())
```

`crawl_all_products` 使用 `celery.group()` 并发调度所有抓取任务。

### 告警机制
tasks 中的 `check_price_alerts()` 在每次抓取后运行。对比最近两条 price_history 记录，若跌幅 >= threshold_percent 则发送飞书通知并更新 `alert.last_notified_price`。

### Docker 服务
- `api` — uvicorn 运行 FastAPI
- `celery_worker` — 抓取任务（并发数=2，速率限制 10/m）
- `celery_beat` — 周期调度器
- `db`（postgres）、`redis` — 基础设施

## 关键约束
- user_id 硬编码为 1（单用户系统）
- 代理：设置 `CRAWL_PROXY_ENABLED=true` 和 `CRAWL_PROXY_URL` 轮换 IP
- 所有时间戳字段使用 UTC 时区（`datetime.now(timezone.utc)`）
- 价格比较使用 Decimal 避免浮点误差