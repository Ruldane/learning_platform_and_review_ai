"""Consentement à Google Agenda et confirmations locales."""

import sqlalchemy as sa

from alembic import op

revision = "0050"
down_revision = "0049"


def _scoped() -> list[sa.Column[object]]:
    return [
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "calendar_connections",
        *_scoped(),
        sa.Column("oauth_state_hash", sa.String(64)),
        sa.Column("oauth_expires_at", sa.DateTime(timezone=True)),
        sa.Column("encrypted_refresh_token", sa.Text()),
        sa.Column("revoke_pending", sa.Boolean(), nullable=False),
        sa.Column("generation", sa.String(36)),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_calendar_connections_user_id", "calendar_connections", ["user_id"])
    op.create_table(
        "calendar_proposals",
        *_scoped(),
        sa.Column("connection_generation", sa.String(36), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("event_id", sa.String(64), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True)),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_calendar_proposals_user_id", "calendar_proposals", ["user_id"])


def downgrade() -> None:
    op.drop_table("calendar_proposals")
    op.drop_table("calendar_connections")
