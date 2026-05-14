"""Resource-level permission helpers."""
from collections.abc import Iterable
from typing import Any

from sqlalchemy import String, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.core.permissions import PERMISSIONS
from app.models.resource_permission import ResourcePermission
from app.models.user import User

RESOURCE_TO_PERMISSION_KEY = {
    ("product", "read"): "product:read",
    ("product", "write"): "product:write",
    ("product", "delete"): "product:delete",
    ("job", "read"): "job:read",
    ("job", "write"): "job:write",
    ("job", "delete"): "job:delete",
    ("user", "read"): "user:read",
    ("user", "write"): "user:manage",
    ("user", "delete"): "user:delete",
}

ACTION_TO_GRANT_PERMISSIONS = {
    "read": {"read", "write", "delete", "*"},
    "write": {"write", "*"},
    "delete": {"delete", "*"},
}


def _validate_resource_action(resource_type: str, action: str) -> None:
    if (resource_type, action) not in RESOURCE_TO_PERMISSION_KEY:
        raise ValueError(f"无效资源权限: {resource_type}:{action}")


def role_allows_permission(user: User, resource_type: str, action: str) -> bool:
    """Return whether the user's role has explicit global resource permission."""
    _validate_resource_action(resource_type, action)
    permission_key = RESOURCE_TO_PERMISSION_KEY[(resource_type, action)]
    return user.role in PERMISSIONS.get(permission_key, set())


async def check_resource_permission(
    db: AsyncSession,
    user: User,
    resource_type: str,
    action: str,
    resource_id: str | int | None = None,
    owner_id: int | None = None,
) -> bool:
    """Check owner, exact ACL, wildcard ACL, then global role fallback."""
    _validate_resource_action(resource_type, action)

    if owner_id is not None and owner_id == user.id:
        return True

    allowed_permissions = ACTION_TO_GRANT_PERMISSIONS[action]
    if resource_id is not None:
        exact_result = await db.execute(
            select(ResourcePermission).where(
                ResourcePermission.subject_id == user.id,
                ResourcePermission.subject_type == "user",
                ResourcePermission.resource_type == resource_type,
                ResourcePermission.resource_id == str(resource_id),
                ResourcePermission.permission.in_(allowed_permissions),
            )
        )
        if exact_result.scalar_one_or_none() is not None:
            return True

    wildcard_result = await db.execute(
        select(ResourcePermission).where(
            ResourcePermission.subject_id == user.id,
            ResourcePermission.subject_type == "user",
            ResourcePermission.resource_type == resource_type,
            ResourcePermission.resource_id == "*",
            ResourcePermission.permission.in_(allowed_permissions),
        )
    )
    if wildcard_result.scalar_one_or_none() is not None:
        return True

    return role_allows_permission(user, resource_type, action)


async def get_user_permitted_resource_ids(
    db: AsyncSession,
    user: User,
    resource_type: str,
    action: str = "read",
) -> tuple[set[str], bool]:
    """Return exact resource IDs and whether a wildcard grant exists."""
    _validate_resource_action(resource_type, action)
    result = await db.execute(
        select(ResourcePermission).where(
            ResourcePermission.subject_id == user.id,
            ResourcePermission.subject_type == "user",
            ResourcePermission.resource_type == resource_type,
            ResourcePermission.permission.in_(ACTION_TO_GRANT_PERMISSIONS[action]),
        )
    )
    exact_ids: set[str] = set()
    has_wildcard = False
    for grant in result.scalars().all():
        if grant.resource_id == "*":
            has_wildcard = True
        else:
            exact_ids.add(str(grant.resource_id))
    return exact_ids, has_wildcard


def accessible_resource_condition(
    user: User,
    resource_type: str,
    action: str,
    owner_column: Any,
    resource_id_column: Any,
) -> Any:
    """Build a SQLAlchemy condition for owner OR ACL access."""
    _validate_resource_action(resource_type, action)
    if role_allows_permission(user, resource_type, action):
        return True

    acl_exists = exists().where(
        ResourcePermission.subject_id == user.id,
        ResourcePermission.subject_type == "user",
        ResourcePermission.resource_type == resource_type,
        or_(
            ResourcePermission.resource_id == func.cast(resource_id_column, String),
            ResourcePermission.resource_id == "*",
        ),
        ResourcePermission.permission.in_(ACTION_TO_GRANT_PERMISSIONS[action]),
    )
    return or_(owner_column == user.id, acl_exists)


async def build_resource_permissions_map(
    db: AsyncSession,
    user: User,
    resource_type: str,
    resources: Iterable[Any],
    *,
    owner_attr: str = "user_id",
) -> dict[str, dict[str, bool]]:
    """Build read/write/delete flags for a set of ORM resources."""
    resource_list = list(resources)
    ids = [str(item.id) for item in resource_list]
    global_flags = {
        "read": role_allows_permission(user, resource_type, "read"),
        "write": role_allows_permission(user, resource_type, "write"),
        "delete": role_allows_permission(user, resource_type, "delete"),
    }
    grant_map: dict[str, set[str]] = {rid: set() for rid in ids}
    grant_map["*"] = set()

    if not ids:
        return {}

    if all(getattr(item, owner_attr, None) == user.id for item in resource_list):
        return {
            str(item.id): {"read": True, "write": True, "delete": True}
            for item in resource_list
        }

    result = await db.execute(
        select(ResourcePermission).where(
            ResourcePermission.subject_id == user.id,
            ResourcePermission.subject_type == "user",
            ResourcePermission.resource_type == resource_type,
            ResourcePermission.resource_id.in_(ids + ["*"]),
        )
    )
    for grant in result.scalars().all():
        grant_map.setdefault(str(grant.resource_id), set()).add(grant.permission)

    permissions: dict[str, dict[str, bool]] = {}
    for item in resource_list:
        rid = str(item.id)
        owner_id = getattr(item, owner_attr, None)
        if owner_id == user.id:
            permissions[rid] = {"read": True, "write": True, "delete": True}
            continue

        grants = grant_map.get(rid, set()) | grant_map.get("*", set())
        permissions[rid] = {
            "read": global_flags["read"] or bool({"read", "write", "delete", "*"} & grants),
            "write": global_flags["write"] or bool({"write", "*"} & grants),
            "delete": global_flags["delete"] or bool({"delete", "*"} & grants),
        }
    return permissions


def apply_accessible_filter(
    query: Select,
    user: User,
    resource_type: str,
    action: str,
    owner_column: Any,
    resource_id_column: Any,
) -> Select:
    """Apply owner OR ACL filter to a query unless role has global access."""
    if role_allows_permission(user, resource_type, action):
        return query
    return query.where(
        accessible_resource_condition(
            user, resource_type, action, owner_column, resource_id_column
        )
    )
