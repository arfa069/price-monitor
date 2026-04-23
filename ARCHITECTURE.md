# Price Monitor - Architecture Document

## Overview

A single-user e-commerce price monitoring system that tracks product prices across Taobao, JD, and Amazon. When price drops are detected, notifications are sent via Feishu Webhook.

## Tech Stack

- **Language**: Python 3.11+
- **Web Framework**: FastAPI (async via asyncio)
- **Database**: PostgreSQL (async via SQLAlchemy)
- **Cache**: Redis
- **Crawler**: Playwright (handles dynamic JS-rendered pages, supports CDP mode)
- **Notification**: Feishu Webhook

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Service Layer                         │
│  POST /config │ POST/GET /products │ GET /history │ POST /alerts│
│  POST /crawl/crawl-now │ GET /crawl/logs │ POST /crawl/cleanup   │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌─────────────────┐   ┌─────────────────────┐
│  PostgreSQL   │   │      Redis      │   │  Playwright Crawler  │
│  (data store)  │   │  (cache layer)  │   │  (in-process async)  │
└───────────────┘   └─────────────────┘   └─────────────────────┘
                          │                         │
                          │            ┌─────────────┼─────────────┐
                          │            ▼             ▼             ▼
                          │     ┌──────────┐  ┌──────────┐  ┌──────────┐
                          │     │  Taobao  │  │   JD    │  │  Amazon  │
                          │     │ Adapter  │  │ Adapter │  │ Adapter  │
                          │     └──────────┘  └──────────┘  └──────────┘
                          │                         │
                          ▼                         ▼
                  ┌─────────────┐           ┌─────────────┐
                  │   Feishu    │           │    CDP /     │
                  │  Webhook    │           │  Launch Mode │
                  └─────────────┘           └─────────────┘
```

## Crawling Strategy

Crawl tasks run **asynchronously in FastAPI's event loop** — no Celery or external worker. The `POST /crawl/crawl-now` endpoint processes each active product sequentially with a 7–12s random interval between crawls to avoid rate limiting.

### Browser Modes

1. **Launch mode** (default): Launches a headless Chromium instance per crawl.
2. **CDP mode**: Connects to an existing browser via Chrome DevTools Protocol (`--remote-debugging-port=9222`). Reuses cookies/login sessions to bypass anti-bot detection.

### Page Load Strategy

- Uses `domcontentloaded` instead of `networkidle` (avoids stalling on ad trackers/WebSocket pings)
- Explicitly waits for price selectors to appear
- Stays 4–6 seconds on each page for full rendering (WebFont loading, especially JD's anti-scraping custom fonts)
- Overall operation timeout: 90s

### Anti-Bot Measures

- CDP mode reuses real browser sessions (with login cookies)
- Randomized delays between page interactions
- Disabled automation-controlled blink feature
- Proxy support for rotating IPs

## Data Model

### users
| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | Primary key |
| feishu_webhook_url | TEXT | Feishu webhook URL |
| crawl_frequency_hours | SMALLINT | Crawl interval (default: 1) |
| data_retention_days | SMALLINT | History retention (default: 365) |
| created_at | TIMESTAMPTZ | Creation timestamp |
| updated_at | TIMESTAMPTZ | Last update timestamp |

### products
| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | Primary key |
| user_id | BIGINT | FK to users |
| platform | VARCHAR(20) | 'taobao', 'jd', 'amazon' |
| url | TEXT | Product URL |
| title | TEXT | Product title |
| active | BOOLEAN | Whether monitoring is active |

### price_history
| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | Primary key |
| product_id | BIGINT | FK to products |
| price | NUMERIC(12,2) | Scraped price |
| currency | VARCHAR(3) | Currency code |
| scraped_at | TIMESTAMPTZ | Scraping timestamp |

### alerts
| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | Primary key |
| product_id | BIGINT | FK to products |
| threshold_percent | NUMERIC(5,2) | Trigger threshold |
| last_notified_at | TIMESTAMPTZ | Last notification time |
| last_notified_price | NUMERIC(12,2) | Price at last notification |
| active | BOOLEAN | Whether alert is active |

### crawl_logs
| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | Primary key |
| product_id | BIGINT | FK to products |
| status | VARCHAR(20) | SUCCESS/ERROR |
| price | NUMERIC(12,2) | Scraped price |
| timestamp | TIMESTAMPTZ | Crawl timestamp |
| error_message | TEXT | Error details if failed |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /config | Configure system settings |
| GET | /health | Health check (database + Redis) |
| POST | /products | Add a product to track |
| GET | /products | List all products |
| GET | /products/{id} | Get product details |
| GET | /products/{id}/history | Get price history |
| POST | /alerts | Create an alert |
| GET | /alerts | List all alerts |
| POST | /crawl/crawl-now | Crawl all active products |
| GET | /crawl/logs | Get recent crawl logs |
| POST | /crawl/cleanup | Delete old data |

## Notification System

- **Feishu Webhook**: JSON payload with text message
- **Idempotency**: Store last_notified_price to prevent duplicate alerts (only notifies if new price is lower than the last notified price)
- **Retry**: 3 attempts with exponential backoff
- **Alert Logic**: Compares the latest two price history records. If the drop percentage >= threshold_percent, sends notification.
- **Payload Format**:
```json
{
  "msg_type": "text",
  "content": {
    "text": "Price Drop Alert: {title_or_url}\nPlatform: {platform}\nOld Price: {old} {currency}\nNew Price: {new} {currency}\nDrop: {percent}%\nLink: {url}"
  }
}
```

## Platform Adapter Pattern

```
app/platforms/base.py     — BasePlatformAdapter (ABC): _init_browser, crawl, extract_price/title
app/platforms/taobao.py   — TaobaoAdapter
app/platforms/jd.py       — JDAdapter
app/platforms/amazon.py   — AmazonAdapter
```

Each adapter implements `extract_price()` and `extract_title()`. The base class manages browser lifecycle (launch or CDP connection), page navigation with timeout handling, and error recovery.

## Data Retention

- Price history and crawl logs retained based on `data_retention_days` (default: 365 days)
- Cleanup triggered via `POST /crawl/cleanup` endpoint
- Accepts a `retention_days` query parameter (capped by config setting)

## Configuration

All settings via environment variables in `.env` (loaded via Pydantic Settings):

| Variable | Description | Default |
|----------|-------------|---------|
| DATABASE_URL | PostgreSQL async connection URL | `postgresql+asyncpg://...` |
| REDIS_URL | Redis connection URL | `redis://localhost:6379/0` |
| REDIS_PASSWORD | Redis password (alternative to URL) | |
| FEISHU_WEBHOOK_URL | Feishu webhook URL for notifications | |
| CDP_ENABLED | Enable CDP mode (connect to existing browser) | `false` |
| CDP_URL | CDP endpoint for existing browser | `http://127.0.0.1:9222` |
| CRAWL_PROXY_ENABLED | Enable proxy for crawling | `false` |
| CRAWL_PROXY_URL | Proxy URL | |
| CRAWL_FREQUENCY_HOURS | Hours between crawls | `1` |
| DATA_RETENTION_DAYS | Days to retain price history | `365` |
| JD_COOKIE | JD cookie string for login session | |
