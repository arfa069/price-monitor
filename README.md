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
| GET | /health | Health check (database + Redis) |
| POST | /config | Configure system settings |
| POST | /products | Add a product to track |
| GET | /products | List all products |
| GET | /products/{id} | Get product details |
| GET | /products/{id}/history | Get price history |
| POST | /alerts | Create an alert |
| GET | /alerts | List all alerts |
| POST | /crawl/crawl-now | Crawl all active products |
| GET | /crawl/logs | Get recent crawl logs |
| POST | /crawl/cleanup | Delete old price history and crawl logs |

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

See `ARCHITECTURE.md` for detailed architecture.

## License

MIT
