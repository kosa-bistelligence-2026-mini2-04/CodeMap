{%- if cookiecutter.enable_teams %}
"""Audit log helpers for recording privileged actions."""

import logging
{%- if cookiecutter.use_postgresql %}
from uuid import UUID
{%- endif %}
from typing import Any

logger = logging.getLogger(__name__)

{%- if cookiecutter.use_postgresql %}


async def record_audit(
    db,
    *,
    actor_user_id: UUID,
    action: str,
    organization_id: UUID | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> None:
    """Persist an audit log entry. Failures are logged but do not raise."""
    try:
        from app.db.models.audit_log import AppAdminAuditLog

        entry = AppAdminAuditLog(
            actor_user_id=actor_user_id,
            action=action,
            organization_id=organization_id,
            target_type=target_type,
            target_id=str(target_id) if target_id is not None else None,
            details=details,
            ip_address=ip_address,
        )
        db.add(entry)
        await db.flush()
    except Exception:
        logger.exception("Failed to write audit log for action=%s actor=%s", action, actor_user_id)

{%- elif cookiecutter.use_sqlite %}


def record_audit(
    db,
    *,
    actor_user_id: str,
    action: str,
    organization_id: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> None:
    """Persist an audit log entry. Failures are logged but do not raise."""
    import json

    try:
        from app.db.models.audit_log import AppAdminAuditLog

        entry = AppAdminAuditLog(
            actor_user_id=actor_user_id,
            action=action,
            organization_id=organization_id,
            target_type=target_type,
            target_id=str(target_id) if target_id is not None else None,
            details=json.dumps(details) if details is not None else None,
            ip_address=ip_address,
        )
        db.add(entry)
        db.flush()
    except Exception:
        logger.exception("Failed to write audit log for action=%s actor=%s", action, actor_user_id)

{%- elif cookiecutter.use_mongodb %}


async def record_audit(
    *,
    actor_user_id: str,
    action: str,
    organization_id: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> None:
    """Persist an audit log entry. Failures are logged but do not raise."""
    try:
        from app.db.models.audit_log import AppAdminAuditLog

        entry = AppAdminAuditLog(
            actor_user_id=actor_user_id,
            action=action,
            organization_id=organization_id,
            target_type=target_type,
            target_id=str(target_id) if target_id is not None else None,
            details=details,
            ip_address=ip_address,
        )
        await entry.insert()
    except Exception:
        logger.exception("Failed to write audit log for action=%s actor=%s", action, actor_user_id)

{%- else %}


async def record_audit(*args: Any, **kwargs: Any) -> None:
    """No-op — database not configured."""

{%- endif %}
{%- else %}
"""Audit log — not configured (enable_teams=false)."""
{%- endif %}
