"""Missions de 48 heures à partir d'offres analysées."""

import sqlalchemy as sa

from alembic import op

revision = "0054"
down_revision = "0053"


def upgrade() -> None:
    op.create_table(
        "missions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("posting_id", sa.String(36), nullable=False),
        sa.Column("posting_title", sa.String(200), nullable=True),
        sa.Column("company", sa.String(200), nullable=True),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("criteria", sa.JSON(), nullable=False),
        sa.Column("submission", sa.JSON(), nullable=True),
        sa.UniqueConstraint("user_id", "posting_id"),
    )
    op.create_index("ix_missions_user_id", "missions", ["user_id"])


def downgrade() -> None:
    op.drop_table("missions")
