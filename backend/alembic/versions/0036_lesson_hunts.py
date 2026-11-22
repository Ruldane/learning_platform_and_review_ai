"""Copie d’exercices qui n’altère pas la leçon publiée."""

import sqlalchemy as sa

from alembic import op

revision = "0036"
down_revision = "0035"


def upgrade() -> None:
    op.create_table(
        "lesson_hunts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "lesson_id",
            sa.String(36),
            sa.ForeignKey("lessons.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("stage", sa.String(12), nullable=False),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("exercise", sa.Text()),
        sa.Column("errors", sa.JSON()),
        sa.Column("responses", sa.JSON()),
        sa.Column("assessment", sa.JSON()),
    )
    op.create_index("ix_lesson_hunts_user_id", "lesson_hunts", ["user_id"])
    op.create_index("ix_lesson_hunts_lesson_id", "lesson_hunts", ["lesson_id"])


def downgrade() -> None:
    op.drop_table("lesson_hunts")
