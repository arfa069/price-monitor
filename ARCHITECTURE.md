# Price Monitor - Architecture Document

## Overview

A multi-user e-commerce price monitoring system that tracks product prices across Taobao, JD, Amazon, and Boss Zhipin job searches. When price drops are detected, notifications are sent via Feishu Webhook.

All API endpoints (except `/auth/register` and `/auth/login`) require JWT authentication. Data is isolated per user — each user can only access their own products, alerts, jobs, and configurations.

## Tech Stack

- **Language**: Python 3.11+
- **Web Framework**: FastAPI (async via asyncio)
- **Database**: PostgreSQL (async via SQLAlchemy)
- **Cache**: Redis
- **Crawler**: Playwright (handles dynamic JS-rendered pages, supports CDP mode)
- **Notification**: Feishu Webhook
- **Frontend**: React + Vite + TypeScript + Ant Design (mobile-responsive, WCAG accessible)

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

### Cron Scheduling

APScheduler (AsyncIOScheduler) is managed by FastAPI's lifespan startup/shutdown. Two scheduler managers handle per-entity cron jobs:

**Product crawl (per-platform)** — `ProductCronScheduler`:
- Each platform (taobao/jd/amazon) gets its own cron expression stored in `product_platform_crons` table
- APScheduler job ID format: `product_cron_{platform}`
- When triggered, calls `crawl_products_by_platform(platform)` — only crawls products of that platform
- API: `GET/POST /products/cron-configs`, `PATCH/DELETE /products/cron-configs/{platform}`
- Frontend: `/schedule` page shows a table with 3 platform rows, add/delete via modal

**Job crawl (per-config)** — `JobConfigScheduler`:
- Each `JobSearchConfig` gets its own cron expression stored in `cron_expression` / `cron_timezone` fields on `job_search_configs`
- APScheduler job ID format: `job_config_cron_{config_id}`
- When triggered, calls `crawl_single_config(config_id)` — only crawls that specific config
- API: `PATCH /jobs/configs/{id}/cron`, `GET /jobs/scheduler/job-configs`
- Frontend: `/schedule` page shows a table of all configs with cron inputs

**Registration**: Both managers are initialized in `main.py:_start_scheduler()`. On startup, `sync_all()` reads the DB and registers jobs for all entities with non-null `cron_expression`.

**Concurrency protection**: A global `asyncio.Semaphore(1)` (shared between cron jobs and manual crawls) prevents overlapping executions.

**Status endpoint**: `GET /scheduler/status` returns all registered jobs in `product_platforms` and `job_configs` objects.

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

> **数据隔离**：所有包含 `user_id` 字段的表（users 除外）均按 `user_id` 隔离查询。用户只能操作属于自己的数据。

### users
| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | Primary key |
| feishu_webhook_url | TEXT | Feishu webhook URL |
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
| product_id | BIGINT | FK to products (NULL for system-level logs) |
| platform | VARCHAR(20) | Platform (nullable) |
| status | VARCHAR(20) | SUCCESS/ERROR/SKIPPED/CRON_SUCCESS/CRON_ERROR |
| price | NUMERIC(12,2) | Scraped price (nullable) |
| timestamp | TIMESTAMPTZ | Crawl timestamp |
| error_message | TEXT | Error details or summary if failed/skipped |

### product_platform_crons
| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | Primary key |
| user_id | BIGINT | FK to users |
| platform | VARCHAR(20) | 'taobao', 'jd', 'amazon' (unique) |
| cron_expression | VARCHAR | 5-segment crontab (nullable) |
| cron_timezone | VARCHAR | Timezone (default: Asia/Shanghai) |
| created_at | TIMESTAMPTZ | Creation timestamp |
| updated_at | TIMESTAMPTZ | Last update timestamp |

### job_search_configs
| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | Primary key |
| user_id | BIGINT | FK to users |
| name | VARCHAR | Config name |
| url | TEXT | Boss search URL |
| active | BOOLEAN | Whether monitoring is active |
| notify_on_new | BOOLEAN | Send notification for new jobs |
| deactivation_threshold | SMALLINT | Consecutive misses before deactivation (default: 3) |
| cron_expression | VARCHAR | Per-config 5-segment crontab (nullable) |
| cron_timezone | VARCHAR | Timezone (default: Asia/Shanghai) |
| created_at | TIMESTAMPTZ | Creation timestamp |
| updated_at | TIMESTAMPTZ | Last update timestamp |

### jobs
| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | Primary key |
| job_id | VARCHAR | Boss securityId (API调用); encryptJobId 用于拼详情页 URL |
| search_config_id | BIGINT | FK to job_search_configs |
| title | TEXT | Job title |
| company | TEXT | Company name |
| company_id | VARCHAR | Boss encryptBrandId |
| salary | VARCHAR | Salary string (e.g. "20-40K") |
| salary_min | INTEGER | Parsed minimum salary (K) |
| salary_max | INTEGER | Parsed maximum salary (K) |
| location | VARCHAR | Job location |
| experience | VARCHAR | Experience requirement |
| education | VARCHAR | Education requirement |
| description | TEXT | Job description (from detail API) |
| address | TEXT | Company address (from detail API) |
| url | TEXT | Job detail URL |
| is_active | BOOLEAN | Whether job is currently listed |
| first_seen_at | TIMESTAMPTZ | First discovery timestamp |
| last_active_at | TIMESTAMPTZ | Last seen in crawl |
| consecutive_miss_count | SMALLINT | Consecutive crawls not seen |
| last_updated_at | TIMESTAMPTZ | Last update timestamp |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /health | Health check (database + Redis + scheduler) |
| GET | /config | Get current configuration |
| POST | /config | Create or update full configuration |
| PATCH | /config | Partial update (feishu url, retention days) |
| POST | /products | Add a product to track |
| GET | /products | List products (paginated) |
| GET | /products/{id} | Get product details |
| GET | /products/{id}/history | Get price history |
| POST | /products/batch-create | Batch import products |
| POST | /products/batch-delete | Batch delete products |
| POST | /products/batch-update | Batch enable/disable products |
| GET | /products/cron-configs | List per-platform cron configs |
| POST | /products/cron-configs | Create per-platform cron config |
| PATCH | /products/cron-configs/{platform} | Update platform cron |
| DELETE | /products/cron-configs/{platform} | Delete platform cron |
| GET | /products/cron-schedules | Next run times for product cron |
| POST | /alerts | Create an alert |
| GET | /alerts | List all alerts |
| POST | /crawl/crawl-now | Crawl all active products |
| GET | /crawl/logs | Get recent crawl logs |
| POST | /crawl/cleanup | Delete old data |
| GET | /scheduler/status | Scheduler job state |
| GET | /jobs/configs | List job search configs |
| POST | /jobs/configs | Create job search config |
| GET | /jobs/configs/{id} | Get job search config |
| PATCH | /jobs/configs/{id} | Update job search config |
| PATCH | /jobs/configs/{id}/cron | Update per-config cron |
| DELETE | /jobs/configs/{id} | Delete job search config |
| GET | /jobs/scheduler/job-configs | Next run times for job cron |
| GET | /jobs | List crawled jobs (paginated) |
| GET | /jobs/{id} | Get job details |
| POST | /jobs/crawl-now | Crawl all active job configs |
| POST | /jobs/crawl-now/{id} | Crawl single job config |

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
backend/app/platforms/base.py     — BasePlatformAdapter (ABC): _init_browser, crawl, extract_price/title
backend/app/platforms/taobao.py   — TaobaoAdapter
backend/app/platforms/jd.py       — JDAdapter
backend/app/platforms/amazon.py   — AmazonAdapter
backend/app/platforms/boss.py    — BossZhipinAdapter (裸 WebSocket CDP + curl_cffi)
```

Each product adapter implements `extract_price()` and `extract_title()`. The base class manages browser lifecycle (launch or CDP connection), page navigation with timeout handling, and error recovery.

### BossZhipinAdapter (Job Crawling)

Unlike product adapters, Boss does NOT use Playwright for crawling. Instead:

- **curl_cffi** with `impersonate="chrome124"` calls the Boss search API directly (TLS-level Chrome fingerprint)
- **Cookies** acquired without search API test (test consumes token): CDP read → disk cache → background tab → homepage
- **Token lifecycle**: `__zp_stoken__` lasts ~5-6 API calls then returns code=37. Automatically refreshed by opening a background tab to search page (~3s). Search/detail API responses only return `__zp_sseed__`, `__zp_sname__`, `__zp_sts__` — NOT new `__zp_stoken__`
- **Cookie domain**: Must use `session.cookies.set(k,v,domain=".zhipin.com")` — `update()` without domain causes old/new token collision
- **Detail fetching**: Sequential 2-5s intervals (no `asyncio.gather`). Retries once on code=37/36 after token refresh. 3 consecutive cookie failures triggers bailout
- **Adapter sharing**: `crawl_all_job_searches` creates one adapter for all configs; `update_job_detail` reuses the passed adapter

This avoids the Playwright CDP `about:blank` redirect that Boss's anti-bot script triggers on detection.

## Data Retention

- Price history and crawl logs retained based on `data_retention_days` (default: 365 days)
- Cleanup triggered via `POST /crawl/cleanup` endpoint
- Accepts a `retention_days` query parameter (capped by config setting)

## Products Pagination

`GET /products` returns paginated results with full metadata:

- **Query params**: `page` (default 1), `size` (default 15, max 100), `platform`, `active`, `keyword`
- **Keyword search**: debounced 400ms, searches title and URL columns
- **Response shape**: `{ items, total, page, page_size, total_pages, has_next, has_prev }`
- **Stable sort**: `ORDER BY created_at DESC, id DESC` — prevents pagination drift on new inserts
- **Auto-rollback**: When batch delete empties the last page, frontend automatically steps back to the previous page

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
| DATA_RETENTION_DAYS | Days to retain price history | `365` |
| JD_COOKIE | JD cookie string for login session | |
