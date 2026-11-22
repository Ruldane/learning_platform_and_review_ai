"""Propositions privées de semaine commune aux programmes."""

import sqlalchemy as sa

from alembic import op

revision = "0060"
down_revision = "0059"


def upgrade() -> None:
    op.create_table(
        "shared_week_proposals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("selection_key", sa.String(64), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("document", sa.JSON(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("user_id", "week_start", "selection_key", "fingerprint"),
    )
    op.create_index("ix_shared_week_proposals_user_id", "shared_week_proposals", ["user_id"])


def downgrade() -> None:
    op.drop_table("shared_week_proposals")
