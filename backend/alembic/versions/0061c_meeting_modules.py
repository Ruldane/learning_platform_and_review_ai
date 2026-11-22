"""Modules privés issus d’un extrait de réunion."""

import sqlalchemy as sa

from alembic import op

revision = "0061c"
down_revision = "0061b"


def upgrade() -> None:
    op.create_table(
        "meeting_modules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(140), nullable=False),
        sa.Column("transcript", sa.Text(), nullable=False),
        sa.Column("source_digest", sa.String(64), nullable=False),
        sa.Column("excerpts", sa.JSON(), nullable=False),
        sa.Column("selection", sa.JSON(), nullable=False),
        sa.Column("module_steps", sa.JSON()),
        sa.Column("published_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_meeting_modules_user_id", "meeting_modules", ["user_id"])


def downgrade() -> None:
    op.drop_table("meeting_modules")
