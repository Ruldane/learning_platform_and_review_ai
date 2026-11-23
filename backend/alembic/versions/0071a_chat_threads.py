"""Listes des conversations du Cerveau et du training."""

import sqlalchemy as sa

from alembic import op

revision = "0071a"
down_revision = "0071"
branch_labels = None
depends_on = None


def _study_index(predicate: str) -> None:
    op.drop_index("uq_study_sessions_open", table_name="study_sessions")
    op.create_index(
        "uq_study_sessions_open",
        "study_sessions",
        ["user_id"],
        unique=True,
        sqlite_where=sa.text(predicate),
    )


def upgrade() -> None:
    op.add_column("conversations", sa.Column("title", sa.String(120), nullable=True))
    op.add_column(
        "conversations", sa.Column("lesson_ids", sa.JSON(), nullable=False, server_default="[]")
    )
    op.add_column("conversation_turns", sa.Column("lesson_ids", sa.JSON(), nullable=True))
    op.add_column(
        "study_sessions", sa.Column("independent", sa.Boolean(), nullable=False, server_default="0")
    )
    op.execute(
        """
        UPDATE conversations AS thread
        SET title = (
            SELECT substr(trim(turn.question), 1, 120)
            FROM conversation_turns AS turn
            WHERE turn.thread_id = thread.id AND turn.user_id = thread.user_id
            ORDER BY turn.created_at, turn.id LIMIT 1
        ),
        updated_at = max(updated_at, coalesce((
            SELECT max(turn.created_at)
            FROM conversation_turns AS turn
            WHERE turn.thread_id = thread.id AND turn.user_id = thread.user_id
        ), updated_at))
        WHERE scope IN ('brain', 'training')
        """
    )
    _study_index("status = 'open' AND independent IS 0")


def downgrade() -> None:
    # L'ancien schéma ne peut rouvrir qu'une séance par compte.
    op.execute(
        """
        UPDATE study_sessions SET status = 'cancelled', ended_at = updated_at
        WHERE status = 'open' AND id IN (
            SELECT id FROM (
                SELECT id, row_number() OVER (
                    PARTITION BY user_id
                    ORDER BY independent, created_at DESC, id DESC
                ) AS rank
                FROM study_sessions WHERE status = 'open'
            ) WHERE rank > 1
        )
        """
    )
    _study_index("status = 'open'")
    op.drop_column("study_sessions", "independent")
    op.drop_column("conversation_turns", "lesson_ids")
    op.drop_column("conversations", "lesson_ids")
    op.drop_column("conversations", "title")
