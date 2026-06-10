{%- if cookiecutter.use_external_user_id_in_conversations %}
"""conversation external_user_id (delegated auth)

Revision ID: 0020_conv_external_user_id
Revises: 0019_user_external_id
Create Date: 2026-05-10T00:00:00+00:00

When --external-user-id is enabled (with --auth-mode=delegated), Conversation
gets a denormalized copy of the resolved User's `external_user_id` so client
APIs can list conversations by their own user identifier — no joins, no
internal UUID leak.
"""

import sqlalchemy as sa

from alembic import op

revision = "0020_conv_external_user_id"
down_revision = "0019_user_external_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("external_user_id", sa.String(255), nullable=True),
    )
    op.create_index(
        "conversations_external_user_id_idx",
        "conversations",
        ["external_user_id"],
    )


def downgrade() -> None:
    op.drop_index("conversations_external_user_id_idx", table_name="conversations")
    op.drop_column("conversations", "external_user_id")
{%- endif %}
