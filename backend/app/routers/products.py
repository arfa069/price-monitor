"""Products API router."""
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.price_history import PriceHistory
from app.models.product import Product, ProductPlatformCron
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.price_history import PriceHistoryResponse
from app.schemas.product import (
    BatchOperationResult,
    ProductBatchCreate,
    ProductBatchCreateItem,
    ProductBatchDelete,
    ProductPlatformCronCreate,
    ProductBatchUpdate,
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductPlatformCronResponse,
    ProductPlatformCronUpdate,
    ProductUpdate,
)

router = APIRouter(prefix="/products", tags=["products"])


def _normalize_tmall_url(url: str) -> str:
    """Extract id and skuId from Taobao/Tmall URL and rebuild full URL.

    Example:
      Input:  https://detail.tmall.com/item.htm?id=xxx&skuId=yyy&other=zzz
      Output: https://detail.tmall.com/item.htm?id=xxx&skuId=yyy
    """
    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    # Extract id (required) and skuId (optional)
    item_id = params.get("id", [None])[0]
    sku_id = params.get("skuId", [None])[0]

    if not item_id:
        return url  # Not a valid Tmall URL, return as-is

    # Rebuild URL with only id and skuId
    query_parts = [f"id={item_id}"]
    if sku_id:
        query_parts.append(f"skuId={sku_id}")

    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{'&'.join(query_parts)}"


def _normalize_product_url(url: str, platform: str) -> str:
    """Normalize product URL based on platform."""
    if platform == "taobao":
        return _normalize_tmall_url(url)
    # Add other platforms if needed
    return url


@router.post("", response_model=ProductResponse)
async def create_product(
    product_data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a new product to track."""
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    # Normalize URL to extract and preserve skuId for Tmall
    normalized_url = _normalize_product_url(product_data.url, product_data.platform)

    product = Product(
        user_id=current_user.id,
        platform=product_data.platform,
        url=normalized_url,
        title=product_data.title,
        active=product_data.active,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


@router.get("", response_model=ProductListResponse)
async def list_products(
    platform: str | None = None,
    active: bool | None = None,
    keyword: str | None = Query(default=None, max_length=200),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=15, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List tracked products with pagination."""
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    base_query = select(Product).where(Product.user_id == current_user.id)

    if platform is not None:
        base_query = base_query.where(Product.platform == platform)
    if active is not None:
        base_query = base_query.where(Product.active == active)
    if keyword is not None:
        # Escape LIKE metacharacters to prevent pattern injection
        escaped = (
            keyword.replace("\\", "\\\\")
                   .replace("%", "\\%")
                   .replace("_", "\\_")
        )
        kw = f"%{escaped}%"
        base_query = base_query.where(
            (Product.title.ilike(kw, escape="\\")) | (Product.url.ilike(kw, escape="\\"))
        )

    # Total count
    count_query = select(func.count()).select_from(base_query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Paginated items
    offset = (page - 1) * size
    items_query = base_query.order_by(desc(Product.created_at), desc(Product.id)).offset(offset).limit(size)
    items_result = await db.execute(items_query)
    items = items_result.scalars().all()

    total_pages = (total + size - 1) // size if total > 0 else 0
    has_prev = page > 1
    has_next = page < total_pages

    return ProductListResponse(
        items=items,
        total=total,
        page=page,
        page_size=size,
        total_pages=total_pages,
        has_next=has_next,
        has_prev=has_prev,
    )


# ── Per-Platform Cron Management (must be before /{product_id} routes) ──

@router.get("/cron-configs", response_model=list[ProductPlatformCronResponse])
async def list_product_cron_configs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all per-platform cron configs for product crawling."""
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    result = await db.execute(
        select(ProductPlatformCron).where(ProductPlatformCron.user_id == current_user.id)
    )
    return result.scalars().all()


@router.post("/cron-configs", response_model=ProductPlatformCronResponse, status_code=201)
async def create_product_cron_config(
    data: ProductPlatformCronCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new per-platform cron config for product crawling."""
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    if data.platform not in ("taobao", "jd", "amazon"):
        raise HTTPException(status_code=400, detail="Invalid platform")

    # Check if already exists
    existing = await db.execute(
        select(ProductPlatformCron).where(
            ProductPlatformCron.platform == data.platform,
            ProductPlatformCron.user_id == current_user.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Platform cron config already exists")

    config = ProductPlatformCron(
        user_id=current_user.id,
        platform=data.platform,
        cron_expression=data.cron_expression,
        cron_timezone=data.cron_timezone or "Asia/Shanghai",
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)

    # Sync scheduler
    if config.cron_expression:
        from app.services.scheduler_job import ProductCronScheduler
        scheduler: ProductCronScheduler = getattr(request.app.state, "product_cron_scheduler", None)
        if scheduler:
            scheduler.add_job(config.platform, config.cron_expression, config.cron_timezone)

    return config


@router.delete("/cron-configs/{platform}")
async def delete_product_cron_config(
    platform: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a per-platform cron config for product crawling."""
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    if platform not in ("taobao", "jd", "amazon"):
        raise HTTPException(status_code=400, detail="Invalid platform")

    result = await db.execute(
        select(ProductPlatformCron).where(
            ProductPlatformCron.platform == platform,
            ProductPlatformCron.user_id == current_user.id,
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Platform cron config not found")

    # Remove scheduler job
    from app.services.scheduler_job import ProductCronScheduler
    scheduler: ProductCronScheduler = getattr(request.app.state, "product_cron_scheduler", None)
    if scheduler:
        scheduler.remove_job(platform)

    await db.delete(config)
    await db.commit()
    return {"message": "Platform cron config deleted"}


@router.patch("/cron-configs/{platform}", response_model=ProductPlatformCronResponse)
async def update_product_cron_config(
    platform: str,
    data: ProductPlatformCronUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update cron expression for a product platform."""
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    if platform not in ("taobao", "jd", "amazon"):
        raise HTTPException(status_code=400, detail="Invalid platform")

    result = await db.execute(
        select(ProductPlatformCron).where(
            ProductPlatformCron.platform == platform,
            ProductPlatformCron.user_id == current_user.id,
        )
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Platform cron config not found")

    config.cron_expression = data.cron_expression
    config.cron_timezone = data.cron_timezone or "Asia/Shanghai"
    await db.commit()
    await db.refresh(config)

    # Sync scheduler
    from app.services.scheduler_job import ProductCronScheduler
    scheduler: ProductCronScheduler = getattr(request.app.state, "product_cron_scheduler", None)
    if scheduler:
        if config.cron_expression:
            scheduler.add_job(config.platform, config.cron_expression, config.cron_timezone)
        else:
            scheduler.remove_job(config.platform)

    return config


@router.get("/cron-schedules")
async def get_product_cron_schedules(request: Request):
    """Get next run times for all per-platform product crawl schedules."""
    from app.services.scheduler_job import ProductCronScheduler
    scheduler: ProductCronScheduler = getattr(request.app.state, "product_cron_scheduler", None)
    if not scheduler:
        return {"platforms": {}}
    return {"platforms": scheduler.get_next_run_times()}


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get product details."""
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.user_id == current_user.id)
    )
    product = result.scalar_one_or_none()

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    return product


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a product."""
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.user_id == current_user.id)
    )
    product = result.scalar_one_or_none()

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = product_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)

    await db.commit()
    await db.refresh(product)
    return product


@router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a product and its related data."""
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.user_id == current_user.id)
    )
    product = result.scalar_one_or_none()

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    await db.delete(product)
    await db.commit()
    return {"message": "Product deleted"}


# --- Batch operations ---


def _detect_platform(url: str) -> str | None:
    """Auto-detect platform from URL."""
    url_lower = url.lower()
    if "jd.com" in url_lower or "item.jd" in url_lower:
        return "jd"
    if "taobao.com" in url_lower or "tmall.com" in url_lower:
        return "taobao"
    if "amazon." in url_lower:
        return "amazon"
    return None


@router.post("/batch-create", response_model=list[BatchOperationResult])
async def batch_create_products(
    batch: ProductBatchCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Batch create products from URLs."""
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    results: list[BatchOperationResult] = []

    # Deduplicate input
    seen_urls: set[str] = set()
    deduped_items: list[ProductBatchCreateItem] = []
    for item in batch.items:
        url = item.url.strip()
        if url in seen_urls:
            results.append(BatchOperationResult(url=url, success=False, error="重复的 URL"))
            continue
        seen_urls.add(url)
        deduped_items.append(item)

    # Check existing URLs in DB (filter by user_id to prevent cross-user URL enumeration)
    existing_urls_result = await db.execute(
        select(Product.url).where(
            Product.url.in_(list(seen_urls)),
            Product.user_id == current_user.id,
        )
    )
    existing_urls = set(existing_urls_result.scalars().all())

    for item in deduped_items:
        url = item.url.strip()
        # Skip if already in DB
        if url in existing_urls:
            results.append(BatchOperationResult(url=url, success=False, error="该 URL 已存在"))
            continue
        # Basic URL format check (schema-level validation for ProductCreate catches most cases)
        if not (url.startswith("http://") or url.startswith("https://")):
            results.append(BatchOperationResult(url=url, success=False, error="URL 格式不正确"))
            continue
        detected = _detect_platform(url)
        platform = item.platform if item.platform else detected
        if not platform:
            results.append(BatchOperationResult(url=url, success=False, error="无法识别平台"))
            continue
        try:
            # Normalize URL to extract and preserve skuId for Tmall
            normalized_url = _normalize_product_url(url, platform)

            product = Product(
                user_id=current_user.id,
                platform=platform,
                url=normalized_url,
                title=item.title,
                active=True,
            )
            db.add(product)
            await db.flush()
            results.append(BatchOperationResult(
                id=product.id, url=normalized_url, success=True
            ))
        except Exception as e:
            results.append(BatchOperationResult(url=url, success=False, error=str(e)))

    await db.commit()
    return results


@router.post("/batch-delete", response_model=list[BatchOperationResult])
async def batch_delete_products(
    payload: ProductBatchDelete,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Batch delete products by IDs."""
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    results: list[BatchOperationResult] = []

    result = await db.execute(
        select(Product).where(Product.id.in_(payload.ids), Product.user_id == current_user.id)
    )
    product_map = {p.id: p for p in result.scalars().all()}
    found_ids = set(product_map.keys())

    for pid in payload.ids:
        if pid not in found_ids:
            results.append(BatchOperationResult(id=pid, success=False, error="商品不存在"))
            continue
        try:
            await db.delete(product_map[pid])
            results.append(BatchOperationResult(id=pid, success=True))
        except Exception as e:
            results.append(BatchOperationResult(id=pid, success=False, error=str(e)))

    try:
        await db.commit()
    except Exception:
        # All results after first error: mark remaining uncommitted as failed
        for result_item in results:
            if result_item.success and result_item.id not in found_ids:
                result_item.success = False
                result_item.error = "批量操作失败"
        raise

    return results


@router.post("/batch-update", response_model=list[BatchOperationResult])
async def batch_update_products(
    payload: ProductBatchUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Batch update products (active status)."""
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    results: list[BatchOperationResult] = []

    result = await db.execute(
        select(Product).where(Product.id.in_(payload.ids), Product.user_id == current_user.id)
    )
    product_map = {p.id: p for p in result.scalars().all()}
    found_ids = set(product_map.keys())

    for pid in payload.ids:
        if pid not in found_ids:
            results.append(BatchOperationResult(id=pid, success=False, error="商品不存在"))
            continue
        try:
            if payload.active is not None:
                product_map[pid].active = payload.active
            results.append(BatchOperationResult(id=pid, success=True))
        except Exception as e:
            results.append(BatchOperationResult(id=pid, success=False, error=str(e)))

    try:
        await db.commit()
    except Exception as e:
        # Mark all as failed if commit fails (nothing persisted)
        for result_item in results:
            if result_item.success:
                result_item.success = False
                result_item.error = str(e)
        return results

    return results


@router.get("/{product_id}/history", response_model=list[PriceHistoryResponse])
async def get_product_history(
    _product_id: int,
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get price history for a product."""
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    # Verify product exists and belongs to user
    result = await db.execute(
        select(Product).where(Product.id == _product_id, Product.user_id == current_user.id)
    )
    product = result.scalar_one_or_none()

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    # Get price history
    cutoff = datetime.now(UTC) - timedelta(days=days)
    result = await db.execute(
        select(PriceHistory)
        .where(
            PriceHistory.product_id == _product_id,
            PriceHistory.scraped_at >= cutoff,
        )
        .order_by(desc(PriceHistory.scraped_at))
        .limit(limit)
    )
    return result.scalars().all()
