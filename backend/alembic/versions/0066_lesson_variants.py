"""Éditions multiformats rattachées à une leçon publiée."""

import sqlalchemy as sa

from alembic import op

revision = "0066"
down_revision = "0065"


def upgrade() -> None:
    op.create_table(
        "lesson_variant_sets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lesson_id", sa.String(36), nullable=False),
        sa.Column("lesson_title", sa.String(200), nullable=False),
        sa.Column("revision", sa.String(64), nullable=False),
        sa.Column("source_markdown", sa.Text(), nullable=False),
        sa.Column("review_markdown", sa.Text(), nullable=False),
        sa.Column("reading_steps", sa.JSON(), nullable=False),
        sa.UniqueConstraint("user_id", "lesson_id", "revision"),
    )
    op.create_index("ix_lesson_variant_sets_user_id", "lesson_variant_sets", ["user_id"])


def downgrade() -> None:
    op.drop_table("lesson_variant_sets")
