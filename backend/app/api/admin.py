"""Admin API routes for user management."""
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import and_, delete, func, or_, select, true
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.security import get_password_hash, require_role
from app.database import get_db
from app.models.audit_log import UserAuditLog
from app.models.user import User
from app.schemas.admin import (
    AdminUserListResponse,
    AdminUserResponse,
    AdminUserUpdate,
    AuditLogListResponse,
    AuditLogResponse,
    UserCreate,
)
from app.schemas.auth import MessageResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/users", tags=["admin"])

# Second router for non-user-specific admin endpoints
admin_router = APIRouter(prefix="/admin", tags=["admin"])


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
    request: Request,
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

    # Role boundary: admin cannot create super_admin
    if current_user.role == "admin" and user_data.role == "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足：仅 super_admin 可创建 super_admin 用户",
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

    await log_audit(
        db=db,
        action="user.create",
        actor_user_id=current_user.id,
        target_type="user",
        target_id=new_user.id,
        details={
            "username": new_user.username,
            "email": new_user.email,
            "role": new_user.role,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:512],
        commit=True,
    )

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
    request: Request,
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

    # Role boundary checks for admin
    if current_user.role == "admin":
        # Admin cannot modify super_admin users
        if user.role == "super_admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足：不能修改 super_admin 用户",
            )
        # Admin cannot promote any user to super_admin
        if update_dict.get("role") == "super_admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足：不能将用户提升为 super_admin",
            )
        # Admin cannot promote themselves to super_admin
        if current_user.id == user_id and "role" in update_dict:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足：不能修改自己的角色",
            )

    # Handle is_active special case (soft delete / restore)
    if "is_active" in update_dict:
        if update_data.is_active is False:
            # Prevent disabling the last active super_admin
            if user.role == "super_admin":
                active_super_count_result = await db.execute(
                    select(func.count(User.id)).where(
                        User.role == "super_admin",
                        User.is_active.is_(True),
                        User.deleted_at.is_(None),
                    )
                )
                active_super_count = active_super_count_result.scalar_one_or_none() or 0
                if active_super_count <= 1:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="不能禁用最后一个活跃的 super_admin",
                    )
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

    await log_audit(
        db=db,
        action="user.update",
        actor_user_id=current_user.id,
        target_type="user",
        target_id=user.id,
        details={"changed_fields": list(update_dict.keys())},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:512],
        commit=True,
    )

    return AdminUserResponse.model_validate(user)


@router.delete("/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: int,
    request: Request,
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

    # Role boundary: admin cannot delete super_admin
    if current_user.role == "admin" and user.role == "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足：不能删除 super_admin 用户",
        )

    # Prevent deleting the last active super_admin
    if user.role == "super_admin":
        active_super_count_result = await db.execute(
            select(func.count(User.id)).where(
                User.role == "super_admin",
                User.is_active.is_(True),
                User.deleted_at.is_(None),
            )
        )
        active_super_count = active_super_count_result.scalar_one_or_none() or 0
        if active_super_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不能删除最后一个活跃的 super_admin",
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

    await log_audit(
        db=db,
        action="user.delete",
        actor_user_id=current_user.id,
        target_type="user",
        target_id=user.id,
        details={"username": user.username},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:512],
        commit=True,
    )

    logger.info(f"Admin {current_user.username} deleted user: {user.username}")
    return MessageResponse(message="用户已删除")


# ── Audit Log Endpoints ───────────────────────────────────────────

@admin_router.get("/audit-logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    actor_user_id: int | None = Query(None, description="按操作者过滤"),
    action: str | None = Query(None, description="按操作类型过滤"),
    current_user: User = Depends(require_role("admin", "super_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated audit logs."""
    base_filter = true()
    if actor_user_id is not None:
        base_filter = and_(base_filter, UserAuditLog.actor_user_id == actor_user_id)
    if action is not None:
        base_filter = and_(base_filter, UserAuditLog.action == action)

    count_query = select(func.count(UserAuditLog.id)).where(base_filter)
    count_result = await db.execute(count_query)
    total = count_result.scalar_one_or_none() or 0

    offset = (page - 1) * page_size
    list_query = (
        select(UserAuditLog)
        .where(base_filter)
        .order_by(UserAuditLog.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    list_result = await db.execute(list_query)
    logs = list_result.scalars().all()

    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
    )
