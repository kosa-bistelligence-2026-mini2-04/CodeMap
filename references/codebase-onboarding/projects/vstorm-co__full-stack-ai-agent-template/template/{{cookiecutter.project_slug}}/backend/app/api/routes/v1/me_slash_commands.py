{%- if cookiecutter.use_postgresql or cookiecutter.use_sqlite %}
"""User-scoped slash command settings.

Routes are nested under ``/me/slash-commands`` because they're always
operating on the current user — there's no cross-user view of these.
"""

from typing import Any
{%- if cookiecutter.use_postgresql %}
from uuid import UUID
{%- endif %}

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, UserSlashCommandSvc
from app.schemas.user_slash_command import (
    BuiltinOverrideUpsert,
    UserSlashCommandCustomCreate,
    UserSlashCommandList,
    UserSlashCommandRead,
    UserSlashCommandUpdate,
)

router = APIRouter()


@router.get("", response_model=UserSlashCommandList)
async def list_slash_commands(service: UserSlashCommandSvc, user: CurrentUser) -> Any:
    """List the current user's custom commands and built-in overrides."""
{%- if cookiecutter.use_postgresql %}
    items, total = await service.list_for_user(user_id=user.id)
{%- elif cookiecutter.use_sqlite %}
    items, total = service.list_for_user(user_id=str(user.id))
{%- endif %}
    return UserSlashCommandList(
        items=[UserSlashCommandRead.model_validate(c) for c in items],
        total=total,
    )


@router.post(
    "/custom",
    response_model=UserSlashCommandRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_custom_command(
    data: UserSlashCommandCustomCreate,
    service: UserSlashCommandSvc,
    user: CurrentUser,
) -> Any:
    """Create a user-defined command with a stored prompt body."""
{%- if cookiecutter.use_postgresql %}
    db_cmd = await service.create_custom(user_id=user.id, data=data)
{%- elif cookiecutter.use_sqlite %}
    db_cmd = service.create_custom(user_id=str(user.id), data=data)
{%- endif %}
    return UserSlashCommandRead.model_validate(db_cmd)


@router.put("/builtin", response_model=UserSlashCommandRead)
async def upsert_builtin_override(
    data: BuiltinOverrideUpsert,
    service: UserSlashCommandSvc,
    user: CurrentUser,
) -> Any:
    """Toggle a built-in command on or off for the current user."""
{%- if cookiecutter.use_postgresql %}
    db_cmd = await service.upsert_builtin_override(
        user_id=user.id, name=data.name, is_enabled=data.is_enabled
    )
{%- elif cookiecutter.use_sqlite %}
    db_cmd = service.upsert_builtin_override(
        user_id=str(user.id), name=data.name, is_enabled=data.is_enabled
    )
{%- endif %}
    return UserSlashCommandRead.model_validate(db_cmd)


@router.patch(
    "/{command_id}",
    response_model=UserSlashCommandRead,
)
async def update_slash_command(
{%- if cookiecutter.use_postgresql %}
    command_id: UUID,
{%- elif cookiecutter.use_sqlite %}
    command_id: str,
{%- endif %}
    data: UserSlashCommandUpdate,
    service: UserSlashCommandSvc,
    user: CurrentUser,
) -> Any:
    """Patch a custom command. Built-in overrides accept only ``is_enabled``."""
{%- if cookiecutter.use_postgresql %}
    db_cmd = await service.update(user_id=user.id, command_id=command_id, data=data)
{%- elif cookiecutter.use_sqlite %}
    db_cmd = service.update(user_id=str(user.id), command_id=command_id, data=data)
{%- endif %}
    return UserSlashCommandRead.model_validate(db_cmd)


@router.delete(
    "/{command_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
async def delete_slash_command(
{%- if cookiecutter.use_postgresql %}
    command_id: UUID,
{%- elif cookiecutter.use_sqlite %}
    command_id: str,
{%- endif %}
    service: UserSlashCommandSvc,
    user: CurrentUser,
) -> Any:
    """Delete a custom command, or remove a built-in override (re-enables it)."""
{%- if cookiecutter.use_postgresql %}
    await service.delete(user_id=user.id, command_id=command_id)
{%- elif cookiecutter.use_sqlite %}
    service.delete(user_id=str(user.id), command_id=command_id)
{%- endif %}
    return None
{%- endif %}
