"""Codes à usage unique et jeton dédié du relais local."""

import sqlalchemy as sa

from alembic import op

revision = "0025"
down_revision = "0024"


def upgrade() -> None:
    op.create_table(
        "mcp_relay_pairings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("code_hash", sa.String(64)),
        sa.Column("code_expires_at", sa.DateTime(timezone=True)),
        sa.Column("token_id", sa.String(36)),
        sa.UniqueConstraint("user_id"),
        sa.UniqueConstraint("code_hash"),
    )
    op.create_index("ix_mcp_relay_pairings_user_id", "mcp_relay_pairings", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_mcp_relay_pairings_user_id", table_name="mcp_relay_pairings")
    op.drop_table("mcp_relay_pairings")
