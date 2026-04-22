# Price Monitor

E-commerce price monitoring system for Taobao, JD, and Amazon with Feishu webhook notifications.

## Features

- Track product prices across multiple platforms
- Automated crawling with Playwright (handles dynamic pages)
- Price drop alerts via Feishu Webhook
- RESTful API for product and alert management

## Quick Start

```powershell
# Install dependencies
pip install -e .

# 1. Configure .env
cp .env.example .env
# 2. Edit .env with your database, Redis, and Feishu webhook URL

# 3. Run migrations
alembic upgrade head

# 4. Start the server
uvicorn app.main:app --reload
```

## Configuration

Create a `.env` file:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/pricemonitor
REDIS_URL=redis://localhost:6379/0
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx

# Platform credentials (optional)
TAOBAO_COOKIE=...
JD_UID=...
AMAZON_EMAIL=...
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Health check |
| POST | /config | Configure system settings |
| POST | /products | Add a product to track |
| GET | /products | List all products |
| GET | /products/{id} | Get product details |
| GET | /products/{id}/history | Get price history |
| POST | /alerts | Create an alert |
| GET | /alerts | List all alerts |
| POST | /crawl/start | Manual crawl trigger |
| GET | /crawl/logs | Get recent crawl logs |

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

- **FastAPI**: Web framework
- **PostgreSQL**: Database (async via SQLAlchemy)
- **Playwright**: Web crawler for dynamic pages
- **Feishu Webhook**: Notification service

See `ARCHITECTURE.md` for detailed architecture.

## License

MIT