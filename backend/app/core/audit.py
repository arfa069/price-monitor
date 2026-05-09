"""Audit logging utilities for tracking administrative and authentication actions.

All audit log entries are written to the `user_audit_logs` table.
By default, log_audit() does NOT commit the transaction — the caller is
responsible for committing alongside their business logic.
"""
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import UserAuditLog

logger = logging.getLogger(__name__)


def _sanitize_details(details: dict[str, Any] | None) -> dict[str, Any] | None:
    """Remove sensitive fields from audit details before persisting."""
    if details is None:
        return None
    sensitive_keys = {
        "password", "hashed_password", "access_token", "token",
        "wechat_access_token", "app_secret", "webhook_url",
    }
    sanitized = {}
    for key, value in details.items():
        if key.lower() in sensitive_keys:
            sanitized[key] = "***REDACTED***"
        else:
            sanitized[key] = value
    return sanitized


async def log_audit(
    db: AsyncSession,
    action: str,
    actor_user_id: int | None = None,
    target_type: str | None = None,
    target_id: int | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    commit: bool = False,
) -> UserAuditLog | None:
    """Write an audit log entry.

    Args:
        db: Database session
        action: Action identifier (e.g. "user.create", "auth.login")
        actor_user_id: User performing the action
        target_type: Type of target (e.g. "user", "config")
        target_id: ID of the target
        details: Additional context (sensitive fields are redacted)
        ip_address: Client IP address
        user_agent: Client user agent string
        commit: If True, commit the session immediately. Default False to allow
                the caller to commit together with business transaction.

    Returns:
        The created UserAuditLog instance, or None if writing failed.
    """
    try:
        log_entry = UserAuditLog(
            actor_user_id=actor_user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=_sanitize_details(details),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(log_entry)
        if commit:
            await db.commit()
        return log_entry
    except Exception:
        logger.warning(
            "Failed to write audit log",
            extra={
                "audit_action": action,
                "audit_actor_user_id": actor_user_id,
                "audit_target_type": target_type,
                "audit_target_id": target_id,
            },
            exc_info=True,
        )
        return None
