"""Config API router."""
import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_permission
from app.core.security import get_password_hash
from app.database import get_db
from app.models.user import User
from app.schemas.user import (
    UserConfigCreate,
    UserConfigDefaults,
    UserConfigResponse,
    UserConfigUpdate,
)
from app.services.user_config_cache import invalidate_user_config_cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["config"])

_DEFAULT_CONFIG = UserConfigDefaults()


async def get_or_create_default_user(db: AsyncSession) -> User:
    """Get the default user or create one if not exists."""
    result = await db.execute(select(User).where(User.username == "default"))
    user = result.scalar_one_or_none()

    if user is None:
        # Create default user
        user = User(
            username="default",
            email="default@localhost",
            hashed_password=get_password_hash("default"),
            is_active=True,
            feishu_webhook_url="",
            data_retention_days=365,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user


@router.post("", response_model=UserConfigResponse)
async def create_or_update_config(
    config_data: UserConfigCreate,
    current_user: User = Depends(require_permission("config:write")),
    db: AsyncSession = Depends(get_db),
):
    """Create or update user configuration."""
    user = await get_or_create_default_user(db)

    user.feishu_webhook_url = config_data.feishu_webhook_url
    user.data_retention_days = config_data.data_retention_days

    await db.commit()
    await db.refresh(user)
    await invalidate_user_config_cache()

    return user


@router.get("", response_model=UserConfigResponse)
async def get_config(
    current_user: User = Depends(require_permission("config:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get current user configuration, or return defaults if not set."""
    user = await get_or_create_default_user(db)
    return user


@router.patch("", response_model=UserConfigResponse)
async def update_config_partial(
    config_data: UserConfigUpdate,
    current_user: User = Depends(require_permission("config:write")),
    db: AsyncSession = Depends(get_db),
):
    """Partial update user configuration (create if not exists)."""
    user = await get_or_create_default_user(db)

    update_data = config_data.model_dump(exclude_unset=True)
    if update_data:
        for field, value in update_data.items():
            setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    await invalidate_user_config_cache()

    return user
