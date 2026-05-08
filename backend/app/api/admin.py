"""Admin API routes for user management."""
import logging
from datetime import UTC, datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, require_role, get_password_hash
from app.database import get_db
from app.models.user import User
from app.schemas.admin import UserCreate, AdminUserUpdate, AdminUserResponse, AdminUserListResponse
from app.schemas.auth import MessageResponse

from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/users", tags=["admin"])


@router.get("", response_model=AdminUserListResponse)
async def list_users(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: str | None = Query(None, description="搜索用户名或邮箱"),
    role: str | None = Query(None, description="按角色过滤"),
    current_user: User = Depends(require_role("admin", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated list of users (non-deleted only)."""
    # Build base query for non-deleted users
    base_filter = User.deleted_at.is_(None)

    if search:
        search_filter = or_(
            User.username.ilike(f"%{search}%"),
            User.email.ilike(f"%{search}%"),
        )
        base_filter = and_(base_filter, search_filter)

    if role:
        base_filter = and_(base_filter, User.role == role)

    # Count total
    count_query = select(func.count(User.id)).where(base_filter)
    count_result = await db.execute(count_query)
    total = count_result.scalar_one_or_none() or 0

    # Get paginated list
    offset = (page - 1) * page_size
    list_query = (
        select(User)
        .where(base_filter)
        .order_by(User.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    list_result = await db.execute(list_query)
    users = list_result.scalars().all()

    return AdminUserListResponse(
        items=[AdminUserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(require_role("admin", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new user (admin only)."""
    # Check username uniqueness (non-deleted users)
    username_query = select(User).where(
        and_(User.username == user_data.username, User.deleted_at.is_(None))
    )
    username_result = await db.execute(username_query)
    if username_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在",
        )

    # Check email uniqueness (non-deleted users)
    email_query = select(User).where(
        and_(User.email == user_data.email, User.deleted_at.is_(None))
    )
    email_result = await db.execute(email_query)
    if email_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已被使用",
        )

    # Create user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        role=user_data.role,
        is_active=True,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    logger.info(f"Admin {current_user.username} created user: {user_data.username}")
    return AdminUserResponse.model_validate(new_user)


@router.get("/{user_id}", response_model=AdminUserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(require_role("admin", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Get a single user by ID (non-deleted only)."""
    query = select(User).where(
        and_(User.id == user_id, User.deleted_at.is_(None))
    )
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    return AdminUserResponse.model_validate(user)


@router.patch("/{user_id}", response_model=AdminUserResponse)
async def update_user(
    user_id: int,
    update_data: AdminUserUpdate,
    current_user: User = Depends(require_role("admin", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Update a user (admin only). Includes soft delete/restore via is_active."""
    # Find user (non-deleted only)
    query = select(User).where(
        and_(User.id == user_id, User.deleted_at.is_(None))
    )
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    # Check username conflict if updating username
    if update_data.username is not None and update_data.username != user.username:
        username_query = select(User).where(
            and_(
                User.username == update_data.username,
                User.deleted_at.is_(None),
                User.id != user_id,
            )
        )
        username_result = await db.execute(username_query)
        if username_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已存在",
            )

    # Check email conflict if updating email
    if update_data.email is not None and update_data.email != user.email:
        email_query = select(User).where(
            and_(
                User.email == update_data.email,
                User.deleted_at.is_(None),
                User.id != user_id,
            )
        )
        email_result = await db.execute(email_query)
        if email_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已被使用",
            )

    # Apply updates
    update_dict = update_data.model_dump(exclude_unset=True)

    # Handle is_active special case (soft delete / restore)
    if "is_active" in update_dict:
        if update_data.is_active is False:
            # Soft delete
            user.deleted_at = datetime.now(UTC)
            user.is_active = False
        elif update_data.is_active is True:
            # Restore
            user.deleted_at = None
            user.is_active = True
        # Remove is_active from update_dict to avoid setting it twice
        del update_dict["is_active"]

    # Apply remaining fields
    for field, value in update_dict.items():
        if value is not None:
            setattr(user, field, value)

    try:
        await db.commit()
        await db.refresh(user)
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"IntegrityError in update_user: {e}")
        error_msg = str(e.orig).lower()
        if 'username' in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已存在",
            )
        elif 'email' in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已被使用",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="数据冲突，请检查用户名或邮箱是否已被使用",
        )

    return AdminUserResponse.model_validate(user)


@router.delete("/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_role("admin", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Soft delete a user and clean up their sessions (admin only)."""
    # Prevent self-delete
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除自己的账号",
        )

    # Find user (non-deleted only)
    query = select(User).where(
        and_(User.id == user_id, User.deleted_at.is_(None))
    )
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    # Soft delete user
    user.deleted_at = datetime.now(UTC)
    user.is_active = False

    # Clean up user's sessions (if Session model exists - Task 9)
    try:
        from app.models.session import Session
        session_delete = delete(Session).where(Session.user_id == user_id)
        await db.execute(session_delete)
    except ImportError:
        pass  # Session model not yet implemented

    await db.commit()

    logger.info(f"Admin {current_user.username} deleted user: {user.username}")
    return MessageResponse(message="用户已删除")