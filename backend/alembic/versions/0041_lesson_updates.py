"""Propositions de mise à jour sur les versions des bibliothèques."""

import sqlalchemy as sa

from alembic import op

revision = "0041"
down_revision = "0040"


def upgrade() -> None:
    op.create_table(
        "lesson_updates",
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
        sa.Column("library", sa.String(120), nullable=False),
        sa.Column("version", sa.String(40), nullable=False),
        sa.Column("source_url", sa.String(2000), nullable=False),
        sa.Column("base_hash", sa.String(64), nullable=False),
        sa.Column("detected", sa.JSON(), nullable=False),
        sa.Column("preparation_session_id", sa.String(36), nullable=False),
        sa.Column("draft", sa.JSON()),
        sa.Column("publication_session_id", sa.String(36)),
        sa.UniqueConstraint("user_id", "lesson_id", "library", "version"),
    )
    op.create_index("ix_lesson_updates_user_id", "lesson_updates", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_lesson_updates_user_id", table_name="lesson_updates")
    op.drop_table("lesson_updates")
