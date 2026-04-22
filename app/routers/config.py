"""Config API router."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserConfigCreate, UserConfigUpdate, UserConfigResponse

router = APIRouter(prefix="/config", tags=["config"])


@router.post("", response_model=UserConfigResponse)
async def create_or_update_config(
    config_data: UserConfigCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create or update user configuration."""
    # For single-user system, always use user_id=1
    result = await db.execute(select(User).where(User.id == 1))
    user = result.scalar_one_or_none()

    if user is None:
        # Create new user
        user = User(
            id=1,
            username="default",
            feishu_webhook_url=config_data.feishu_webhook_url,
            crawl_frequency_hours=config_data.crawl_frequency_hours,
            data_retention_days=config_data.data_retention_days,
        )
        db.add(user)
    else:
        # Update existing user
        user.feishu_webhook_url = config_data.feishu_webhook_url
        user.crawl_frequency_hours = config_data.crawl_frequency_hours
        user.data_retention_days = config_data.data_retention_days

    await db.commit()
    await db.refresh(user)
    return user


@router.get("", response_model=UserConfigResponse)
async def get_config(db: AsyncSession = Depends(get_db)):
    """Get current user configuration."""
    result = await db.execute(select(User).where(User.id == 1))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=404, detail="Configuration not found")

    return user