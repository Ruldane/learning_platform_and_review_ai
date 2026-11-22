"""Expériences privées avec deux références figées et mesure observée."""

import sqlalchemy as sa

from alembic import op

revision = "0058b"
down_revision = "0058a"


def upgrade() -> None:
    op.create_table(
        "watch_experiments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(140), nullable=False),
        sa.Column("sources", sa.JSON(), nullable=False),
        sa.Column("protocol", sa.Text(), nullable=False),
        sa.Column("criterion", sa.Text(), nullable=False),
        sa.Column("observation", sa.JSON()),
        sa.Column("completed", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_watch_experiments_user_id", "watch_experiments", ["user_id"])


def downgrade() -> None:
    op.drop_table("watch_experiments")
