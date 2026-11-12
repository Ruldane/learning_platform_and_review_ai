"""learning (objectifs, tableaux, programmes, leçons, ressources, compétences)

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-12 10:00:00.000000

"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


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


def _b(name: str) -> sa.Column[Any]:
    return sa.Column(name, sa.Boolean(), nullable=False)


def _dt(name: str, null: bool = False) -> sa.Column[Any]:
    return sa.Column(name, sa.DateTime(timezone=True), nullable=null)


def _fk(table: str, column: str, target: str, on: str = "CASCADE") -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column],
        [f"{target}.id"],
        name=op.f(f"fk_{table}_{column}_{target}"),
        ondelete=on,
    )


def _uq(table: str, *columns: str) -> sa.UniqueConstraint:
    return sa.UniqueConstraint(*columns, name=op.f(f"uq_{table}_{columns[0]}"))


def _create(table: str, *items: Any, indexes: dict[str, list[str]] | None = None) -> None:
    """Crée la table avec les colonnes communes (`UserScopedMixin`) et ses index."""
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


def _create_goals_and_boards() -> None:
    _create(
        "goals",
        _t("text"),
        _s("target_role", 120, True),
        _d("deadline", True),
        _i("weekly_minutes", True),
        _s("status", 16),
        _j("framing"),
        _t("minutes", True),
        _s("council_session_id", 36, True),
    )
    _create(
        "boards",
        _s("goal_id", 36),
        _s("session_id", 36, True),
        _i("step"),
        _s("kind", 16),
        _s("title", 200),
        _t("mermaid"),
        _j("scene", True),
        _s("author", 16),
        _s("parent_id", 36, True),
        _s("scribe_key", 80, True),
        _fk("boards", "goal_id", "goals"),
        _uq("boards", "user_id", "scribe_key"),
    )
    _create(
        "proposals",
        _s("goal_id", 36),
        _s("session_id", 36),
        _i("batch"),
        _i("rank"),
        _s("name", 120),
        _t("promise"),
        _i("duration_weeks"),
        _i("weekly_hours"),
        _j("skills"),
        _t("final_project"),
        _j("tradeoffs"),
        _s("board_id", 36, True),
        _b("chosen"),
        _fk("proposals", "goal_id", "goals"),
        _fk("proposals", "board_id", "boards", "SET NULL"),
        _uq("proposals", "session_id", "batch", "rank"),
        indexes={"ix_proposals_user_goal": ["user_id", "goal_id"]},
    )


def _create_program_and_weeks() -> None:
    _create(
        "programs",
        _s("goal_id", 36),
        _s("title", 200),
        _i("version"),
        _s("status", 16),
        _d("start_date"),
        _i("weekly_minutes"),
        _i("cap_minutes"),
        _s("session_id", 36, True),
        _dt("validated_at", True),
        _fk("programs", "goal_id", "goals"),
    )
    _create(
        "weeks",
        _s("program_id", 36),
        _i("rank"),
        _s("theme", 200),
        _t("objective"),
        _t("deliverable"),
        _d("start_date"),
        _fk("weeks", "program_id", "programs"),
        _uq("weeks", "program_id", "rank"),
    )


def _create_modules_and_tasks() -> None:
    _create(
        "modules",
        _s("week_id", 36),
        _s("program_id", 36),
        _i("rank"),
        _s("title", 200),
        _j("skills"),
        _j("prerequisites"),
        _b("skipped"),
        _fk("modules", "week_id", "weeks"),
        _uq("modules", "week_id", "rank"),
    )
    _create(
        "tasks",
        _s("module_id", 36),
        _s("program_id", 36),
        _i("rank"),
        _s("title", 200),
        _s("type", 16),
        _i("minutes"),
        _t("done_criterion"),
        _d("planned_date"),
        _s("status", 8),
        _b("already_known"),
        _fk("tasks", "module_id", "modules"),
        indexes={
            "ix_tasks_program_id": ["program_id"],
            "ix_tasks_user_planned": ["user_id", "planned_date"],
        },
    )


def _create_plan_versions() -> None:
    _create(
        "plan_versions",
        _s("program_id", 36),
        _i("version"),
        _j("snapshot"),
        _j("diff", True),
        _s("reason", 300),
        _s("session_id", 36, True),
        _i("revision", True),
        _dt("accepted_at", True),
        _fk("plan_versions", "program_id", "programs"),
        _uq("plan_versions", "program_id", "version"),
        _uq("plan_versions", "user_id", "session_id", "revision"),
    )


def _create_lesson_tables() -> None:
    _create(
        "lessons",
        _s("module_id", 36),
        _s("program_id", 36),
        _s("title", 200),
        _t("markdown"),
        _i("word_count"),
        _s("status", 16),
        _s("pdf_key", 200, True),
        _i("attempts"),
        _s("failure_reason", 300, True),
        _s("session_id", 36, True),
        _j("report", True),
        _fk("lessons", "module_id", "modules"),
        _uq("lessons", "module_id"),
    )
    _create(
        "resources",
        _s("module_id", 36),
        _s("program_id", 36),
        _s("source_id", 36, True),
        _s("type", 16),
        _t("title"),
        _t("url"),
        _s("url_hash", 64),
        _t("author", True),
        _s("published", 32, True),
        _s("lang", 8, True),
        _i("duration_minutes", True),
        _s("level", 16, True),
        _s("reason", 300),
        _i("score", True),
        _s("local_key", 200, True),
        _t("note", True),
        _s("status", 8),
        _fk("resources", "module_id", "modules"),
        _uq("resources", "module_id", "url_hash"),
        indexes={"ix_resources_user_program": ["user_id", "program_id"]},
    )


def _create_skill_tables() -> None:
    _create(
        "skills",
        _s("name", 120),
        _s("norm_name", 120),
        _s("domain", 120, True),
        _j("synonyms"),
        _uq("skills", "user_id", "norm_name"),
    )
    _create(
        "skill_edges",
        _s("before_id", 36),
        _s("after_id", 36),
        _fk("skill_edges", "before_id", "skills"),
        _fk("skill_edges", "after_id", "skills"),
        _uq("skill_edges", "before_id", "after_id"),
    )
    _create(
        "user_skills",
        _s("skill_id", 36),
        _s("level", 16),
        _j("evidence"),
        _fk("user_skills", "skill_id", "skills"),
        _uq("user_skills", "user_id", "skill_id"),
    )


def upgrade() -> None:
    """Upgrade schema."""
    _create_goals_and_boards()
    _create_program_and_weeks()
    _create_modules_and_tasks()
    _create_plan_versions()
    _create_lesson_tables()
    _create_skill_tables()


def downgrade() -> None:
    """Downgrade schema."""
    # Enfants avant parents (clés étrangères) ; les index suivent leur table.
    for tables in (
        ("user_skills", "skill_edges", "skills", "resources", "lessons"),
        ("plan_versions", "tasks", "modules", "weeks", "programs"),
        ("proposals", "boards", "goals"),
    ):
        for table in tables:
            op.drop_table(table)
