"""Tests for resource permission checking logic."""
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.resource_permission import (
    check_resource_permission,
    get_user_permitted_resource_ids,
    role_allows_permission,
)


def _user(role: str):
    u = MagicMock(spec=User)
    u.id = 1
    u.role = role
    u.is_active = True
    return u


class TestRoleAllowsPermission:
    """Test role_allows_permission only grants explicit global resource permissions."""

    def test_product_read_forbidden_for_user(self):
        u = _user("user")
        assert role_allows_permission(u, "product", "read") is False

    def test_product_delete_forbidden_for_user(self):
        u = _user("user")
        assert role_allows_permission(u, "product", "delete") is False

    def test_product_delete_forbidden_for_admin(self):
        u = _user("admin")
        assert role_allows_permission(u, "product", "delete") is False

    def test_product_delete_allowed_for_super_admin(self):
        u = _user("super_admin")
        assert role_allows_permission(u, "product", "delete") is True

    def test_unknown_resource_type_returns_false(self):
        u = _user("admin")
        with pytest.raises(ValueError):
            role_allows_permission(u, "unknown_type", "read")


class TestCheckResourcePermission:
    """Test check_resource_permission cascades: owner -> exact -> wildcard -> role."""

    @pytest.mark.asyncio
    async def test_invalid_resource_type_raises(self):
        u = _user("admin")
        with pytest.raises(ValueError, match="无效"):
            await check_resource_permission(MagicMock(spec=AsyncSession), u, "bad", "read")

    @pytest.mark.asyncio
    async def test_unknown_action_raises(self):
        u = _user("admin")
        with pytest.raises(ValueError, match="无效"):
            await check_resource_permission(
                MagicMock(spec=AsyncSession), u, "product", "unknown_action"
            )

    @pytest.mark.asyncio
    async def test_exact_match_returns_true(self):
        mock_db = AsyncMock(spec=AsyncSession)
        u = _user("user")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock()
        mock_db.execute.return_value = mock_result

        result = await check_resource_permission(mock_db, u, "product", "delete", "123")
        assert result is True

    @pytest.mark.asyncio
    async def test_wildcard_match_falls_back_from_no_exact(self):
        mock_db = AsyncMock(spec=AsyncSession)
        u = _user("user")
        exact_result = MagicMock()
        exact_result.scalar_one_or_none.return_value = None
        wildcard_result = MagicMock()
        wildcard_result.scalar_one_or_none.return_value = MagicMock()
        mock_db.execute.side_effect = [exact_result, wildcard_result]

        result = await check_resource_permission(mock_db, u, "product", "read", "999")
        assert result is True

    @pytest.mark.asyncio
    async def test_role_fallback_when_no_resource_permission(self):
        mock_db = AsyncMock(spec=AsyncSession)
        u = _user("user")
        no_result = MagicMock()
        no_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = no_result

        result = await check_resource_permission(mock_db, u, "product", "read", "456")
        assert result is False

    @pytest.mark.asyncio
    async def test_owner_implicit_allow_without_acl(self):
        mock_db = AsyncMock(spec=AsyncSession)
        u = _user("user")

        result = await check_resource_permission(
            mock_db, u, "product", "write", "456", owner_id=u.id
        )
        assert result is True
        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_admin_role_lacks_resource_delete_fallback(self):
        mock_db = AsyncMock(spec=AsyncSession)
        u = _user("admin")
        no_result = MagicMock()
        no_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = no_result

        result = await check_resource_permission(mock_db, u, "product", "delete", "123")
        assert result is False

    @pytest.mark.asyncio
    async def test_super_admin_role_allows_delete_via_role_fallback(self):
        mock_db = AsyncMock(spec=AsyncSession)
        u = _user("super_admin")
        no_result = MagicMock()
        no_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = no_result

        result = await check_resource_permission(mock_db, u, "product", "delete", "123")
        assert result is True

    @pytest.mark.asyncio
    async def test_star_permission_grants_all_actions(self):
        mock_db = AsyncMock(spec=AsyncSession)
        u = _user("user")
        exact_result = MagicMock()
        exact_result.scalar_one_or_none.return_value = MagicMock(
            permission="*", resource_id="200"
        )
        mock_db.execute.return_value = exact_result

        for action in ["read", "write", "delete"]:
            result = await check_resource_permission(
                mock_db, u, "product", action, "200"
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_wildcard_resource_id_grants_all_resources(self):
        mock_db = AsyncMock(spec=AsyncSession)
        u = _user("user")
        exact_result = MagicMock()
        exact_result.scalar_one_or_none.return_value = None
        wildcard_result = MagicMock()
        wildcard_result.scalar_one_or_none.return_value = MagicMock(
            permission="read", resource_id="*"
        )
        mock_db.execute.side_effect = [exact_result, wildcard_result]

        result = await check_resource_permission(mock_db, u, "product", "read", "99999")
        assert result is True


class TestGetUserPermittedResourceIds:
    """Boundary coverage for batch preload."""

    @pytest.mark.asyncio
    async def test_empty_permissions_returns_empty_ids_no_wildcard(self):
        mock_db = AsyncMock(spec=AsyncSession)
        u = _user("user")
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        exact_ids, has_wildcard = await get_user_permitted_resource_ids(
            mock_db, u, "product"
        )
        assert exact_ids == set()
        assert has_wildcard is False

    @pytest.mark.asyncio
    async def test_exact_ids_and_wildcard_separated(self):
        mock_db = AsyncMock(spec=AsyncSession)
        u = _user("user")
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            MagicMock(resource_id="10", permission="read"),
            MagicMock(resource_id="20", permission="write"),
            MagicMock(resource_id="*", permission="read"),
        ]
        mock_db.execute.return_value = mock_result

        exact_ids, has_wildcard = await get_user_permitted_resource_ids(
            mock_db, u, "product"
        )
        assert exact_ids == {"10", "20"}
        assert has_wildcard is True

    @pytest.mark.asyncio
    async def test_wildcard_only_no_exact_ids(self):
        mock_db = AsyncMock(spec=AsyncSession)
        u = _user("user")
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            MagicMock(resource_id="*", permission="*"),
        ]
        mock_db.execute.return_value = mock_result

        exact_ids, has_wildcard = await get_user_permitted_resource_ids(
            mock_db, u, "product"
        )
        assert exact_ids == set()
        assert has_wildcard is True
