{%- if cookiecutter.use_delegated_auth %}
"""user external_user_id for delegated auth

Revision ID: 0019_user_external_id
Revises: 0018_user_slash_commands
Create Date: 2026-05-10T00:00:00+00:00

When --auth-mode=delegated, the User table needs a stable external ID minted
by the IdP (the JWT `sub` claim). First valid token from a fresh user
auto-creates a row keyed by this column.
"""

import sqlalchemy as sa

from alembic import op

revision = "0019_user_external_id"
down_revision = "0018_user_slash_commands"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("external_user_id", sa.String(255), nullable=True),
    )
    op.create_unique_constraint(
        "users_external_user_id_key", "users", ["external_user_id"]
    )
    op.create_index(
        "users_external_user_id_idx", "users", ["external_user_id"]
    )


def downgrade() -> None:
    op.drop_index("users_external_user_id_idx", table_name="users")
    op.drop_constraint("users_external_user_id_key", "users", type_="unique")
    op.drop_column("users", "external_user_id")
{%- endif %}
