{%- if cookiecutter.use_postgresql or cookiecutter.use_sqlite or cookiecutter.use_mongodb %}
"""Grant or revoke the app-admin flag on a user account.

Usage:
    project cmd create-app-admin user@example.com
    project cmd create-app-admin user@example.com --revoke
"""
{%- if cookiecutter.use_postgresql or cookiecutter.use_mongodb %}
import asyncio
{%- endif %}

import click

from app.commands import command, error, success, warning


@command("create-app-admin", help="Grant (or revoke) app-admin privileges for a user")
@click.argument("email")
@click.option("--revoke", is_flag=True, default=False, help="Revoke app-admin instead of granting it")
def create_app_admin(email: str, revoke: bool) -> None:
{%- if cookiecutter.use_postgresql %}
    asyncio.run(_run(email, revoke))


async def _run(email: str, revoke: bool) -> None:
    from app.db.session import get_db_context
    from app.repositories import user_repo

    async with get_db_context() as db:
        user = await user_repo.get_by_email(db, email)
        if not user:
            error(f"No user found with email: {email}")
            return

        if revoke:
            if not getattr(user, "is_app_admin", False):
                warning(f"{email} is not an app admin — nothing to revoke.")
                return
            user.is_app_admin = False
            await db.flush()
            await db.refresh(user)
            success(f"App-admin privileges revoked for {email}.")
        else:
            if getattr(user, "is_app_admin", False):
                warning(f"{email} is already an app admin.")
                return
            user.is_app_admin = True
            await db.flush()
            await db.refresh(user)
            success(f"App-admin privileges granted to {email}.")

{%- elif cookiecutter.use_sqlite %}
    from app.db.session import get_db_session
    from app.repositories import user_repo

    with next(get_db_session()) as db:
        user = user_repo.get_by_email(db, email)
        if not user:
            error(f"No user found with email: {email}")
            return

        if revoke:
            if not getattr(user, "is_app_admin", False):
                warning(f"{email} is not an app admin — nothing to revoke.")
                return
            user.is_app_admin = False
            db.flush()
            db.refresh(user)
            success(f"App-admin privileges revoked for {email}.")
        else:
            if getattr(user, "is_app_admin", False):
                warning(f"{email} is already an app admin.")
                return
            user.is_app_admin = True
            db.flush()
            db.refresh(user)
            success(f"App-admin privileges granted to {email}.")

{%- elif cookiecutter.use_mongodb %}
    asyncio.run(_run(email, revoke))


async def _run(email: str, revoke: bool) -> None:
    from app.db.session import init_db
    from app.repositories import user_repo

    await init_db()
    user = await user_repo.get_by_email(email)
    if not user:
        error(f"No user found with email: {email}")
        return

    if revoke:
        if not getattr(user, "is_app_admin", False):
            warning(f"{email} is not an app admin — nothing to revoke.")
            return
        user.is_app_admin = False
        await user.save()
        success(f"App-admin privileges revoked for {email}.")
    else:
        if getattr(user, "is_app_admin", False):
            warning(f"{email} is already an app admin.")
            return
        user.is_app_admin = True
        await user.save()
        success(f"App-admin privileges granted to {email}.")

{%- endif %}
{%- else %}
"""create-app-admin command — not available without a database."""
{%- endif %}
