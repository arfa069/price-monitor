"""Products API router."""
from typing import List
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.database import get_db
from app.models.product import Product
from app.models.price_history import PriceHistory
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse, ProductDetail
from app.schemas.price_history import PriceHistoryResponse

router = APIRouter(prefix="/products", tags=["products"])


@router.post("", response_model=ProductResponse)
async def create_product(
    product_data: ProductCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add a new product to track."""
    product = Product(
        user_id=1,  # Single user system
        platform=product_data.platform,
        url=product_data.url,
        title=product_data.title,
        active=product_data.active,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


@router.get("", response_model=List[ProductResponse])
async def list_products(
    platform: str | None = None,
    active: bool | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List all tracked products."""
    query = select(Product).where(Product.user_id == 1)

    if platform is not None:
        query = query.where(Product.platform == platform)
    if active is not None:
        query = query.where(Product.active == active)

    query = query.order_by(desc(Product.created_at))
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{product_id}", response_model=ProductDetail)
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    """Get product details with recent price history and alerts."""
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.user_id == 1)
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
):
    """Update a product."""
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.user_id == 1)
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
async def delete_product(product_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a product and its related data."""
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.user_id == 1)
    )
    product = result.scalar_one_or_none()

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    await db.delete(product)
    await db.commit()
    return {"message": "Product deleted"}


@router.get("/{product_id}/history", response_model=List[PriceHistoryResponse])
async def get_product_history(
    product_id: int,
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """Get price history for a product."""
    # Verify product exists and belongs to user
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.user_id == 1)
    )
    product = result.scalar_one_or_none()

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    # Get price history
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(PriceHistory)
        .where(
            PriceHistory.product_id == product_id,
            PriceHistory.scraped_at >= cutoff,
        )
        .order_by(desc(PriceHistory.scraped_at))
        .limit(limit)
    )
    return result.scalars().all()