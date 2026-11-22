"""Sélection et rappel privés de reprise après une pause."""

import sqlalchemy as sa

from alembic import op

revision = "0065"
down_revision = "0063"


def upgrade() -> None:
    op.create_table(
        "study_returns",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("selection", sa.JSON(), nullable=True),
        sa.Column("prepared_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reminder_on", sa.Date(), nullable=True),
        sa.Column("training_id", sa.String(36), nullable=True),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_study_returns_user_id", "study_returns", ["user_id"])


def downgrade() -> None:
    op.drop_table("study_returns")
