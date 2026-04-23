# Price Monitor

E-commerce price monitoring system for Taobao, JD, and Amazon with Feishu webhook notifications.

## Features

- Track product prices across multiple platforms
- Automated crawling with Playwright (handles dynamic JS-rendered pages)
- Price drop alerts via Feishu Webhook
- CDP mode: reuse an existing browser session to bypass login walls and anti-bot detection
- RESTful API for product and alert management

## Quick Start

```powershell
# Install dependencies
pip install -e .

# 1. Create and edit .env
# Required: DATABASE_URL, REDIS_URL, FEISHU_WEBHOOK_URL
# See the Configuration section below for the full .env content.

# 2. Run migrations
alembic upgrade head

# 3. Start the server
uvicorn app.main:app
```

> **Windows note**: Do **not** add `--reload` — it breaks Playwright's subprocess handling. Use `uvicorn app.main:app` or `python -m app.main` instead.

## Configuration

Create a `.env` file:

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

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Health check (database + Redis + scheduler) |
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
| GET | /scheduler/status | Scheduler status (started/not_started) |

## Development

```powershell
# Run linter
ruff check .

# Run tests
pytest

# Run with coverage
coverage run -m pytest
coverage report
```

## Architecture

- **FastAPI**: Web framework (async via asyncio)
- **PostgreSQL**: Database (async via SQLAlchemy)
- **Playwright**: Web crawler for dynamic pages (launch or CDP mode)
- **Redis**: Cache layer
- **Feishu Webhook**: Notification service

Crawl tasks run **directly in FastAPI's async context** — no Celery or background worker needed. Each crawl uses a 90s timeout with platform-specific price selectors.

### Cron Scheduling (APScheduler)

The system supports two scheduling modes:
- **Interval mode**: Crawl every N hours (default: 1 hour)
- **Cron mode**: Crawl on a cron schedule (e.g., `0 9 * * *` = daily at 9:00)

Scheduler runs as an AsyncIOScheduler managed by FastAPI's lifespan. Configured via:
```
# Interval mode (POST /config)
crawl_frequency_hours: 2

# Cron mode (PATCH /config)
crawl_cron: "0 9 * * *"
crawl_timezone: "Asia/Shanghai"
```

The two modes are mutually exclusive. Switching modes updates the scheduler job immediately (hot-reload).

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
