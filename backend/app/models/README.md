# Models

This directory contains SQLAlchemy ORM models for the price monitoring system.

## Model Relationships

```
User (1) ──────< Product (N)
                    │
                    ├──< PriceHistory (N)
                    ├──< Alert (N)
                    └──< CrawlLog (N)
```

## Usage

Import models from `app.models`:

```python
from app.models import User, Product, PriceHistory, Alert, CrawlLog
```

## Indexes

- `products`: (user_id, platform, active)
- `products_price_history`: (product_id, scraped_at DESC)
- `crawl_logs`: (product_id, timestamp DESC)