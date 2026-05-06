# Price Monitor

E-commerce price monitoring system for Taobao, JD, and Amazon with Feishu webhook notifications.

## Features

- Track product prices across multiple platforms (Taobao, JD, Amazon, Boss Zhipin)
- Automated crawling with Playwright (handles dynamic JS-rendered pages)
- Price drop alerts via Feishu Webhook
- CDP mode: reuse an existing browser session to bypass login walls and anti-bot detection
- Per-product crawl schedule (cron support per product)
- Job search monitoring for Boss Zhipin
- RESTful API for product and alert management
- Mobile-responsive UI with accessibility support (WCAG compliance)

## Quick Start

```powershell
# Install dependencies
cd backend && pip install -e .

# 1. Create and edit .env at project root
# Required: DATABASE_URL, REDIS_URL, FEISHU_WEBHOOK_URL
# See the Configuration section below for the full .env content.

# 2. Run migrations
cd backend && alembic upgrade head

# 3. Start the server
cd backend && uvicorn app.main:app
```

> **Windows note**: Do **not** add `--reload` — it breaks Playwright's subprocess handling. Use `python -m uvicorn app.main:app` or `uvicorn app.main:app` instead (without `--reload`).

## Configuration

Create a `.env` file at the project root:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/pricemonitor
REDIS_URL=redis://localhost:6379/0
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx

# CDP mode — connect to an already-running browser (e.g. Edge/Chrome started with --remote-debugging-port=9222)
# This lets you reuse login sessions to bypass anti-bot detection
CDP_ENABLED=true
CDP_URL=http://127.0.0.1:9222

# Proxy (optional, for rotating IPs)
CRAWL_PROXY_ENABLED=false
CRAWL_PROXY_URL=http://user:pass@host:port

# Platform credentials (optional)
JD_COOKIE=...
```

## API Endpoints

> **认证说明**：除 `/auth/register` 和 `/auth/login` 外，所有 API 调用都需要在请求头中携带 `Authorization: Bearer <token>`。未带 token 的请求返回 401。

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Health check (database + Redis + scheduler) | 否 |
| GET | /config | Get current configuration |
| POST | /config | Create or update full configuration |
| PATCH | /config | Partial update configuration (cron/tz/hours) |
| POST | /products | Add a product to track |
| GET | /products | List products (paginated: page, size, total, etc.) |
| GET | /products/{id} | Get product details |
| GET | /products/{id}/history | Get price history |
| POST | /products/batch-create | Batch import products |
| POST | /products/batch-delete | Batch delete products |
| POST | /products/batch-update | Batch enable/disable products |
| POST | /alerts | Create an alert |
| GET | /alerts | List all alerts |
| POST | /crawl/crawl-now | Crawl all active products |
| GET | /crawl/logs | Get recent crawl logs |
| POST | /crawl/cleanup | Delete old price history and crawl logs |
| GET | /scheduler/status | Scheduler status (both product and job crawl) |
| GET/POST | /jobs/configs | List/Create job search configs |
| GET/PATCH/DELETE | /jobs/configs/{id} | Manage a job search config |
| GET | /jobs | List crawled jobs (paginated) |
| POST | /jobs/crawl-now | Crawl all active job configs |
| POST | /jobs/crawl-now/{id} | Crawl single job config |
| GET/PUT | /config/job-crawl-cron | Get/Update job crawl schedule |

## 认证 API

系统使用 JWT Token 进行身份验证。

### 端点

| Method | Path | Description | 认证 |
|--------|------|-------------|------|
| POST | /auth/register | 注册新用户 | 否 |
| POST | /auth/login | 用户登录 | 否 |
| POST | /auth/logout | 用户登出 | 是 |
| GET | /auth/me | 获取当前用户信息 | 是 |

### 注册

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "email": "test@example.com", "password": "123456"}'
```

**请求体：**
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | 是 | 用户名（3-50字符） |
| email | string | 是 | 邮箱地址 |
| password | string | 是 | 密码（至少6位） |

**响应（201 Created）：**
```json
{
  "id": 1,
  "username": "testuser",
  "email": "test@example.com",
  "is_active": true,
  "created_at": "2026-05-06T10:30:00Z"
}
```

### 登录

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "123456"}'
```

**响应（200 OK）：**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 访问受保护资源

登录后，在请求头中携带 Token：

```bash
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### 错误码

| 状态码 | 含义 | 说明 |
|--------|------|------|
| 201 | 注册成功 | 新用户创建成功 |
| 200 | 登录/登出成功 | 操作成功 |
| 400 | 用户名或邮箱已注册 | 注册时用户名或邮箱冲突 |
| 401 | 认证失败 | 用户名/密码错误或 Token 过期 |
| 422 | 参数验证失败 | 密码太短、邮箱格式错误等 |
| 429 | 请求过于频繁 | 连续5次登录失败后锁定15分钟 |

### 安全机制

- **登录失败锁定**：连续5次登录失败后，账户将被锁定15分钟
- **Token 有效期**：24小时
- **密码加密**：使用 bcrypt 算法加密存储
- **数据隔离**：所有数据按 `user_id` 隔离，用户只能访问自己的数据
- **强制认证**：除 `/auth/register` 和 `/auth/login` 外，所有接口均需认证

## Development

```powershell
# Run linter
cd backend && ruff check .

# Run tests
cd backend && pytest

# Run with coverage
cd backend && coverage run -m pytest
cd backend && coverage report

# Start frontend
cd frontend && npm run dev
```

## Architecture

- **FastAPI**: Web framework (async via asyncio)
- **PostgreSQL**: Database (async via SQLAlchemy)
- **Playwright**: Web crawler for dynamic pages (launch or CDP mode)
- **Redis**: Cache layer
- **Feishu Webhook**: Notification service

Crawl tasks run **directly in FastAPI's async context** — no Celery or background worker needed. Each crawl uses a 90s timeout with platform-specific price selectors.

### Cron Scheduling (APScheduler)

The system supports two independent cron jobs:

**Product crawl** — two mutually exclusive modes:
- **Interval mode**: Crawl every N hours (default: 1 hour)
- **Cron mode**: Crawl on a cron schedule (e.g., `0 9 * * *` = daily at 9:00)

Configured via `GET/POST/PATCH /config`:
```
# Interval mode
crawl_frequency_hours: 2

# Cron mode
crawl_cron: "0 9 * * *"
crawl_timezone: "Asia/Shanghai"
```

**Job crawl** — always cron mode (default `"0 9 * * *"`, configured via `GET/PUT /config/job-crawl-cron`).

Both cron jobs are managed via the **Schedule page** (`/schedule`) in the frontend, which shows registration state, next run time, and provides independent save buttons.

Concurrent crawl protection: both cron and manual crawls share a global `asyncio.Semaphore(1)` — only one crawl runs at a time. On cron failure, a CrawlLog entry is written and a Feishu notification is sent if configured.

### Products Pagination

`GET /products` supports pagination with full metadata:
```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "page_size": 15,
  "total_pages": 7,
  "has_next": true,
  "has_prev": false
}
```

Query parameters: `page` (default 1), `size` (default 15, max 100), `platform`, `active`, `keyword` (debounced search by title/URL).

See `ARCHITECTURE.md` for detailed architecture.

## License

MIT
