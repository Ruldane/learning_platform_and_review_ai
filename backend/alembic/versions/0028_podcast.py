"""Épisodes du podcast quotidien."""

import sqlalchemy as sa

from alembic import op

revision = "0028"
down_revision = "0027"


def upgrade() -> None:
    op.create_table(
        "podcast_episodes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("lesson_id", sa.String(36), nullable=False),
        sa.Column("module_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("script", sa.JSON()),
        sa.Column("session_id", sa.String(36)),
        sa.Column("audio_key", sa.String(180)),
        sa.Column("duration_seconds", sa.Integer()),
        sa.UniqueConstraint("user_id", "day"),
    )
    op.create_index("ix_podcast_episodes_user_id", "podcast_episodes", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_podcast_episodes_user_id", table_name="podcast_episodes")
    op.drop_table("podcast_episodes")
