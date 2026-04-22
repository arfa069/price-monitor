# Price Monitor - Architecture Document

## Overview

A single-user e-commerce price monitoring system that tracks product prices across Taobao, JD, and Amazon. When price drops are detected, notifications are sent via Feishu Webhook.

## Tech Stack

- **Language**: Python 3.11+
- **Web Framework**: FastAPI
- **Database**: PostgreSQL (async via SQLAlchemy)
- **Cache**: Redis
- **Crawler**: Playwright (handles dynamic JS-rendered pages)
- **Notification**: Feishu Webhook

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Service Layer                         │
│  POST /config │ POST/GET /products │ GET /history │ POST /alerts│
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌─────────────────┐   ┌─────────────────────┐
│  PostgreSQL   │   │      Redis      │   │   Celery Worker     │
│  (data store)  │   │  (broker+cache) │   │   (crawl tasks)      │
└───────────────┘   └─────────────────┘   └─────────────────────┘
                                                 │
                              ┌──────────────────┼──────────────────┐
                              ▼                  ▼                  ▼
                        ┌──────────┐      ┌──────────┐       ┌──────────┐
                        │  Taobao  │      │   JD    │       │  Amazon  │
                        │ Adapter  │      │ Adapter │       │ Adapter  │
                        └──────────┘      └──────────┘       └──────────┘
                                                 │
                                                 ▼
                                          ┌─────────────┐
                                          │   Feishu    │
                                          │  Webhook    │
                                          └─────────────┘
```

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
| GET | /health | Health check |
| POST | /products | Add a product to track |
| GET | /products | List all products |
| GET | /products/{id} | Get product details |
| GET | /products/{id}/history | Get price history |
| POST | /alerts | Create an alert |
| GET | /alerts | List all alerts |
| POST | /crawl/start | Manual crawl trigger |
| GET | /crawl/logs | Get recent crawl logs |

## Crawling Strategy

1. **Platform Adapters**: Each platform (Taobao, JD, Amazon) has a dedicated adapter
2. **Playwright**: Used for dynamic page rendering (JS-rendered content)
3. **Rate Limiting**: Max 1 request per 1-2 seconds per product
4. **Anti-Bot**: Randomized user agents, viewport, and delays
5. **Retry Logic**: Exponential backoff for transient failures

## Notification System

- **Feishu Webhook**: JSON payload with text message
- **Idempotency**: Store last_notified_price to prevent duplicate alerts
- **Retry**: 3 attempts with exponential backoff (1m, 5m, 15m)
- **Payload Format**:
```json
{
  "msg_type": "text",
  "content": {
    "text": "Price Drop Alert: [Product] on [Platform] dropped from ¥{old} to ¥{new}. Link: {url}"
  }
}
```

## Data Retention

- Price history retained for 1 year (configurable)
- Automatic prune job runs daily
- Crawl logs retained for 30 days