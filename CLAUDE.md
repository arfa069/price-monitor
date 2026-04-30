# CLAUDE.md

此文件为 Claude Code (claude.ai/code) 提供代码库操作指南。

## 项目概览

淘宝、京东、亚马逊价格监控系统 + Boss 直聘职位搜索监控。通过 Playwright 抓取商品页面/职位信息，记录价格历史，降价时通过飞书 Webhook 发送通知。

**技术栈**：Python 3.11+ · FastAPI · PostgreSQL (async SQLAlchemy) · Redis · Playwright · 飞书 Webhook
**前端**：React + Vite + TypeScript + Ant Design

## 常用命令

```powershell
# 安装依赖
cd backend && pip install -e .

# 运行数据库迁移
cd backend && alembic upgrade head

# 启动开发服务器
cd backend && python -m uvicorn app.main:app
# 注意：Windows 上不要用 --reload，会导致 Playwright 子进程报错

# 运行测试
cd backend && pytest

# 代码检查
cd backend && ruff check .

# 启动前端
cd frontend && npm run dev

# Docker Compose 完整启动
docker-compose up -d
```

## 架构

### 入口文件
- `backend/app/main.py` — FastAPI 应用工厂，含 lifespan、路由注册、/health 检查
- `backend/app/config.py` — Pydantic Settings，环境变量

### 前端路由
- `/jobs` — 职位管理（搜索配置 + 职位列表 + 全量/单配置爬取）
- `/products` — 商品管理（商品列表 + 商品爬取 + 爬取记录）
- `/schedule` — 定时配置（三卡片：频率模式选择、商品/职位 cron 编辑、数据保留设置）

### 平台适配器模式
```
backend/app/platforms/base.py     — BasePlatformAdapter (ABC)：_init_browser、crawl、extract_price/title（抽象方法）
backend/app/platforms/taobao.py   — TaobaoAdapter
backend/app/platforms/jd.py       — JDAdapter
backend/app/platforms/amazon.py  — AmazonAdapter
backend/app/platforms/boss.py    — BossAdapter (裸 WebSocket CDP + curl_cffi)
```
每个适配器实现 `extract_price()` 和 `extract_title()`。基类负责 Playwright 生命周期管理（每次抓取 90s 超时，支持代理/CDP 模式）。

### 数据库模式
所有数据库操作用 `async with AsyncSessionLocal() as db:` 配合 `await db.commit()`。
- `backend/app/database.py` — 异步引擎、AsyncSessionLocal、get_db 依赖注入
- `backend/app/models/` — SQLAlchemy 模型：User、Product、PriceHistory、Alert、CrawlLog、JobSearchConfig、Job
- `backend/alembic/versions/` — 迁移文件

### 商品抓取流程（`POST /crawl/crawl-now`）
- `_crawl_one()` 在 FastAPI async 上下文中直接运行，无 Celery 依赖
- `check_price_alerts()` 在每次抓取后对比最近两条价格记录，跌幅达标则发飞书通知
- `POST /crawl/cleanup` 手动触发旧数据清理

### Boss 职位抓取流程（`POST /jobs/crawl-now`）
- `BossZhipinAdapter.crawl()` 通过 curl_cffi 调 Boss 搜索 API，不依赖 Playwright 浏览器
- Cookie 获取四层降级：磁盘缓存 → CDP 读取 → 新 tab 刷新 → curl_cffi 主页刷新
- `process_job_results()` 去重入库，`update_job_detail()` 串行获取职位详情（2-5s 间隔）
- `crawl_all_job_searches()` 中所有 config 共享同一个 adapter 实例，避免重复获取 cookie 导致浏览器 tab 泛滥
- crawl_detail 的 `_ensure_cookies()` 有 5 分钟时间戳缓存，同一 adapter 实例内跳过重复获取

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
