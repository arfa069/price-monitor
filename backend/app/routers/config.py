"""Config API router."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.user import (
    UserConfigCreate,
    UserConfigDefaults,
    UserConfigResponse,
    UserConfigUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["config"])

_DEFAULT_CONFIG = UserConfigDefaults()


@router.post("", response_model=UserConfigResponse)
async def create_or_update_config(
    config_data: UserConfigCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create or update user configuration."""
    result = await db.execute(select(User).where(User.id == 1))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            id=1,
            username="default",
            feishu_webhook_url=config_data.feishu_webhook_url,
            data_retention_days=config_data.data_retention_days,
        )
        db.add(user)
    else:
        user.feishu_webhook_url = config_data.feishu_webhook_url
        user.data_retention_days = config_data.data_retention_days

    await db.commit()
    await db.refresh(user)

    return user


@router.get("", response_model=UserConfigResponse)
async def get_config(db: AsyncSession = Depends(get_db)):
    """Get current user configuration, or return defaults if not set."""
    result = await db.execute(select(User).where(User.id == 1))
    user = result.scalar_one_or_none()

    if user is None:
        return UserConfigResponse(
            id=0,
            username="default",
            feishu_webhook_url="",
            data_retention_days=_DEFAULT_CONFIG.data_retention_days,
        )

    return user


@router.patch("", response_model=UserConfigResponse)
async def update_config_partial(
    config_data: UserConfigUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Partial update user configuration (create if not exists)."""
    result = await db.execute(select(User).where(User.id == 1))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            id=1,
            username="default",
            feishu_webhook_url="",
            data_retention_days=_DEFAULT_CONFIG.data_retention_days,
        )
        db.add(user)

    update_data = config_data.model_dump(exclude_unset=True)
    if update_data:
        for field, value in update_data.items():
            setattr(user, field, value)

    await db.commit()
    await db.refresh(user)

    return user
