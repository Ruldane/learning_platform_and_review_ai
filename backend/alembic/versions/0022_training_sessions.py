"""Session training sans leçon imposée, dans le même créneau que la séance guidée."""

import sqlalchemy as sa

from alembic import op

revision = "0022"
down_revision = "0021"

SCOPE = (
    "(kind = 'guided' AND lesson_id IS NOT NULL AND module_id IS NOT NULL "
    "AND program_id IS NOT NULL) OR "
    "(kind = 'training' AND lesson_id IS NULL AND module_id IS NULL AND program_id IS NULL)"
)


def _index() -> None:
    op.create_index(
        "uq_study_sessions_open",
        "study_sessions",
        ["user_id"],
        unique=True,
        sqlite_where=sa.text("status = 'open'"),
    )


def upgrade() -> None:
    op.drop_index("uq_study_sessions_open", table_name="study_sessions")
    with op.batch_alter_table("study_sessions") as batch:
        batch.add_column(sa.Column("kind", sa.String(16), nullable=False, server_default="guided"))
        for name in ("lesson_id", "module_id", "program_id"):
            batch.alter_column(name, existing_type=sa.String(36), nullable=True)
        batch.create_check_constraint("study_scope", SCOPE)
    _index()
    op.add_column("conversation_turns", sa.Column("mode", sa.String(16)))
    op.add_column("conversation_turns", sa.Column("practice", sa.JSON))


def downgrade() -> None:
    op.drop_column("conversation_turns", "practice")
    op.drop_column("conversation_turns", "mode")
    op.execute("DELETE FROM conversations WHERE scope = 'training'")
    op.execute("DELETE FROM study_sessions WHERE kind = 'training'")
    op.drop_index("uq_study_sessions_open", table_name="study_sessions")
    with op.batch_alter_table("study_sessions") as batch:
        batch.drop_constraint("study_scope", type_="check")
        for name in ("lesson_id", "module_id", "program_id"):
            batch.alter_column(name, existing_type=sa.String(36), nullable=False)
        batch.drop_column("kind")
    _index()
