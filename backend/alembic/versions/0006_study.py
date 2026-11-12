"""study (quiz, fiches, sessions d'étude, journal, relevés) et colonnes de la phase 5

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-12 14:00:00.000000

"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Enfants avant parents (clés étrangères) ; les index suivent leur table.
STUDY_TABLES = (
    "quiz_attempts",
    "quiz_questions",
    "quizzes",
    "flashcards",
    "study_sessions",
    "skill_snapshots",
    "journal_entries",
)


def _s(name: str, length: int, null: bool = False) -> sa.Column[Any]:
    return sa.Column(name, sa.String(length=length), nullable=null)


def _t(name: str, null: bool = False) -> sa.Column[Any]:
    return sa.Column(name, sa.Text(), nullable=null)


def _i(name: str, null: bool = False) -> sa.Column[Any]:
    return sa.Column(name, sa.Integer(), nullable=null)


def _d(name: str, null: bool = False) -> sa.Column[Any]:
    return sa.Column(name, sa.Date(), nullable=null)


def _j(name: str, null: bool = False) -> sa.Column[Any]:
    return sa.Column(name, sa.JSON(), nullable=null)


def _dt(name: str, null: bool = False) -> sa.Column[Any]:
    return sa.Column(name, sa.DateTime(timezone=True), nullable=null)


def _fk(table: str, column: str, target: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column], [f"{target}.id"], name=op.f(f"fk_{table}_{column}_{target}"), ondelete="CASCADE"
    )


def _uq(table: str, *columns: str) -> sa.UniqueConstraint:
    return sa.UniqueConstraint(*columns, name=op.f(f"uq_{table}_{columns[0]}"))


def _create(
    table: str,
    *items: Any,
    indexes: dict[str, list[str]] | None = None,
    partial: dict[str, tuple[list[str], str]] | None = None,
) -> None:
    """Crée la table avec les colonnes communes (`UserScopedMixin`), ses index et ses index
    uniques partiels (`nom → (colonnes, condition)`)."""
    op.create_table(
        table,
        *items,
        _s("id", 36),
        _s("user_id", 36),
        _dt("created_at"),
        _dt("updated_at"),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{table}")),
    )
    with op.batch_alter_table(table, schema=None) as batch_op:
        batch_op.create_index(batch_op.f(f"ix_{table}_user_id"), ["user_id"], unique=False)
        for name, columns in (indexes or {}).items():
            batch_op.create_index(name, columns, unique=False)
        for name, (columns, where) in (partial or {}).items():
            batch_op.create_index(name, columns, unique=True, sqlite_where=sa.text(where))


def _create_quiz_tables() -> None:
    _create(
        "quizzes",
        _s("module_id", 36),
        _s("program_id", 36),
        _s("title", 200),
        _s("status", 16),
        _s("session_id", 36, True),
        _s("failure_reason", 300, True),
        _fk("quizzes", "module_id", "modules"),
        _uq("quizzes", "module_id"),
    )
    _create(
        "quiz_questions",
        _s("quiz_id", 36),
        _i("rank"),
        _s("type", 8),
        _t("prompt"),
        _t("code", True),
        _j("choices"),
        _i("correct_index", True),
        _t("expected"),
        _j("rubric"),
        _t("explanation"),
        _s("skill", 120),
        _fk("quiz_questions", "quiz_id", "quizzes"),
        _uq("quiz_questions", "quiz_id", "rank"),
    )
    _create(
        "quiz_attempts",
        _s("quiz_id", 36),
        _j("answers"),
        _s("status", 8),
        _i("score", True),
        _j("results", True),
        _s("session_id", 36, True),
        _dt("graded_at", True),
        _d("retry_on", True),
        _j("followup", True),
        _fk("quiz_attempts", "quiz_id", "quizzes"),
        indexes={"ix_quiz_attempts_user_quiz": ["user_id", "quiz_id"]},
        partial={"uq_quiz_attempts_grading": (["user_id", "quiz_id"], "status = 'grading'")},
    )


def _create_study_tables() -> None:
    _create(
        "flashcards",
        _t("front"),
        _t("back"),
        _s("front_hash", 64),
        _s("skill", 120, True),
        _s("module_id", 36, True),
        _s("source", 8),
        _s("source_id", 36, True),
        _i("step"),
        _d("due_date"),
        _d("last_reviewed_on", True),
        _uq("flashcards", "user_id", "front_hash"),
        indexes={"ix_flashcards_user_due": ["user_id", "due_date"]},
    )
    _create(
        "study_sessions",
        _s("lesson_id", 36),
        _s("module_id", 36),
        _s("program_id", 36),
        _s("mode", 16),
        _s("status", 16),
        _s("session_id", 36, True),
        _t("question", True),
        _j("task_ids"),
        _i("worked_minutes", True),
        _i("minutes"),
        _dt("ended_at", True),
        _t("summary", True),
        _j("outcome", True),
        partial={"uq_study_sessions_open": (["user_id"], "status = 'open'")},
    )


def _create_journal_tables() -> None:
    _create(
        "journal_entries",
        _s("kind", 16),
        _t("text"),
        _d("occurred_on"),
        _s("ref_key", 120, True),
        _s("session_id", 36, True),
        _s("study_session_id", 36, True),
        _s("quiz_attempt_id", 36, True),
        _s("memory_item_id", 36, True),
        _j("data"),
        _uq("journal_entries", "user_id", "ref_key"),
        indexes={"ix_journal_entries_user_created": ["user_id", "created_at"]},
    )
    _create(
        "skill_snapshots",
        _d("week_start"),
        _j("levels"),
        _uq("skill_snapshots", "user_id", "week_start"),
    )


def _add_columns() -> None:
    with op.batch_alter_table("user_skills", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("fail_streak", sa.Integer(), nullable=False, server_default="0")
        )
    with op.batch_alter_table("plan_versions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("kind", sa.String(8), nullable=False, server_default="build"))
        batch_op.add_column(
            sa.Column("status", sa.String(12), nullable=False, server_default="pending")
        )
        batch_op.add_column(sa.Column("base_fingerprint", sa.String(64), nullable=True))
        batch_op.add_column(sa.Column("review_entry_id", sa.String(36), nullable=True))
        batch_op.add_column(sa.Column("week_loads", sa.JSON(), nullable=True))
    # Les versions de la phase 4 : acceptées si January les a acceptées, sinon des brouillons
    # remplacés (la phase 4 n'écrivait pas de proposition en attente).
    op.execute(
        "UPDATE plan_versions SET status = "
        "CASE WHEN accepted_at IS NOT NULL THEN 'accepted' ELSE 'superseded' END"
    )


def upgrade() -> None:
    """Upgrade schema."""
    _create_quiz_tables()
    _create_study_tables()
    _create_journal_tables()
    _add_columns()


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("plan_versions", schema=None) as batch_op:
        for column in ("week_loads", "review_entry_id", "base_fingerprint", "status", "kind"):
            batch_op.drop_column(column)
    with op.batch_alter_table("user_skills", schema=None) as batch_op:
        batch_op.drop_column("fail_streak")
    for table in STUDY_TABLES:
        op.drop_table(table)
