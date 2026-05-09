"""Permission-based access control using FastAPI dependencies.

This module provides fine-grained permission checks beyond simple role-based
access. Permissions are checked via FastAPI Depends() to ensure consistent
security across all routers.
"""
from fastapi import Depends, HTTPException, status

from app.core.security import get_current_user
from app.models.user import User

# Permission to role mapping
PERMISSIONS = {
    "user:read": {"admin", "super_admin"},
    "user:manage": {"admin", "super_admin"},
    "user:delete": {"admin", "super_admin"},
    "crawl:execute": {"user", "super_admin"},
    "crawl:read_logs": {"user", "admin", "super_admin"},
    "schedule:read": {"user", "admin", "super_admin"},
    "schedule:configure": {"super_admin"},
    "config:read": {"admin", "super_admin"},
    "config:write": {"user", "admin", "super_admin"},
}


def require_permission(permission: str):
    """Return a FastAPI dependency that checks if the user has the given permission.

    Usage:
        @router.post("/crawl-now", dependencies=[Depends(require_permission("crawl:execute"))])
    """
    async def checker(current_user: User = Depends(get_current_user)) -> User:
        allowed_roles = PERMISSIONS.get(permission)
        if allowed_roles is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"未知权限: {permission}",
            )
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足",
            )
        return current_user
    return checker
