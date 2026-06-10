{%- if cookiecutter.enable_teams and cookiecutter.enable_rag and cookiecutter.use_jwt and (cookiecutter.use_postgresql or cookiecutter.use_sqlite) %}
"""add active_knowledge_base_ids to conversations

Revision ID: 0009_conv_active_kb_ids
Revises: 0008_backfill_default_kbs
Create Date: {{ cookiecutter.generated_at }}

Adds the optional JSONB (PostgreSQL) / TEXT (SQLite) column
`active_knowledge_base_ids` to `conversations`.

Semantics:
  NULL  → use defaults: personal + org KBs active, app KBs off
  []    → RAG disabled for this conversation
  [id1] → explicit KB selection
"""

import sqlalchemy as sa
from alembic import op
{%- if cookiecutter.use_postgresql %}
from sqlalchemy.dialects.postgresql import JSONB
{%- endif %}

revision = "0009_conv_active_kb_ids"
down_revision = "0008_backfill_default_kbs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column(
            "active_knowledge_base_ids",
{%- if cookiecutter.use_postgresql %}
            JSONB(),
{%- else %}
            sa.Text(),
{%- endif %}
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("conversations", "active_knowledge_base_ids")


{%- else %}
"""add active_knowledge_base_ids to conversations — skipped (enable_teams/enable_rag/use_jwt=false or no SQL DB)

Revision ID: 0009_conv_active_kb_ids
"""

revision = "0009_conv_active_kb_ids"
down_revision = "0008_backfill_default_kbs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
{%- endif %}
