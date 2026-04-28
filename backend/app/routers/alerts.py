"""Alerts API router."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.alert import Alert
from app.models.product import Product
from app.schemas.alert import AlertCreate, AlertResponse, AlertUpdate

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("", response_model=AlertResponse)
async def create_alert(
    alert_data: AlertCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new price alert."""
    # Verify product exists and belongs to user
    result = await db.execute(
        select(Product).where(Product.id == alert_data.product_id, Product.user_id == 1)
    )
    product = result.scalar_one_or_none()

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    alert = Alert(
        product_id=alert_data.product_id,
        alert_type="price_drop",
        threshold_percent=alert_data.threshold_percent,
        active=alert_data.active,
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert


@router.get("", response_model=list[AlertResponse])
async def list_alerts(
    product_id: int | None = None,
    active: bool | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List all alerts."""
    query = select(Alert).join(Product).where(Product.user_id == 1)

    if product_id is not None:
        query = query.where(Alert.product_id == product_id)
    if active is not None:
        query = query.where(Alert.active == active)

    query = query.order_by(desc(Alert.created_at))
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    """Get alert details."""
    result = await db.execute(
        select(Alert).join(Product).where(Alert.id == alert_id, Product.user_id == 1)
    )
    alert = result.scalar_one_or_none()

    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    return alert


@router.patch("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: int,
    alert_data: AlertUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an alert."""
    result = await db.execute(
        select(Alert).join(Product).where(Alert.id == alert_id, Product.user_id == 1)
    )
    alert = result.scalar_one_or_none()

    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    update_data = alert_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(alert, field, value)

    await db.commit()
    await db.refresh(alert)
    return alert


@router.delete("/{alert_id}")
async def delete_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    """Delete an alert."""
    result = await db.execute(
        select(Alert).join(Product).where(Alert.id == alert_id, Product.user_id == 1)
    )
    alert = result.scalar_one_or_none()

    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    await db.delete(alert)
    await db.commit()
    return {"message": "Alert deleted"}
