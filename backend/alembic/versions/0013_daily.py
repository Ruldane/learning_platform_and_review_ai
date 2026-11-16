"""quotidien : projets, relevés du radar, briefs du jour, registre des passages planifiés

Revision ID: 0013
Revises: 0012
Create Date: 2026-11-16 10:00:00.000000

"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0013"
down_revision: str | Sequence[str] | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DAILY_TABLES = ("jobs", "briefs", "radar_runs", "projects")


def _s(name: str, length: int, null: bool = False) -> sa.Column[Any]:
    return sa.Column(name, sa.String(length=length), nullable=null)


def _i(name: str, null: bool = False) -> sa.Column[Any]:
    return sa.Column(name, sa.Integer(), nullable=null)


def _j(name: str, null: bool = False) -> sa.Column[Any]:
    return sa.Column(name, sa.JSON(), nullable=null)


def _dt(name: str, null: bool = False) -> sa.Column[Any]:
    return sa.Column(name, sa.DateTime(timezone=True), nullable=null)


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


def _create_projects() -> None:
    _create(
        "projects",
        _s("module_id", 36),
        _s("program_id", 36),
        _s("title", 200),
        _j("brief", True),
        _s("status", 16),
        _s("session_id", 36, True),
        _i("brief_attempts"),
        _j("submissions"),
        _j("evaluation", True),
        _j("drafts"),
        _dt("validated_at", True),
        _i("profile_version", True),
        sa.UniqueConstraint("user_id", "module_id", name=op.f("uq_projects_user_id")),
    )


def _create_radar_runs() -> None:
    _create(
        "radar_runs",
        _s("role", 120),
        _s("zone", 120),
        _s("role_norm", 120),
        _s("zone_norm", 120),
        _s("trigger", 16),
        _s("period", 16, True),
        _s("status", 16),
        _s("session_id", 36, True),
        _i("queries"),
        _i("candidates"),
        _i("read_count"),
        _i("blocked_count"),
        _i("not_postings"),
        _i("analyzed"),
        _j("blocked_domains"),
        _j("postings"),
        _j("ranking"),
        _j("alerts"),
        _s("previous_id", 36, True),
        _dt("finished_at", True),
        indexes={"ix_radar_runs_user_created": ["user_id", "created_at"]},
    )


def _create_briefs_and_jobs() -> None:
    _create(
        "briefs",
        sa.Column("day", sa.Date(), nullable=False),
        _s("origin", 16),
        _j("sections"),
        _j("offer_keys"),
        _j("resource", True),
        _j("advice", True),
        _s("advice_status", 16),
        _s("session_id", 36, True),
        sa.UniqueConstraint("user_id", "day", name=op.f("uq_briefs_user_id")),
    )
    _create(
        "jobs",
        _s("name", 40),
        _s("period", 16),
        _s("status", 16),
        _dt("started_at"),
        _dt("finished_at", True),
        _i("attempts"),
        _s("error_code", 64, True),
        _s("ref_id", 36, True),
        _dt("next_due_at", True),
        sa.UniqueConstraint("user_id", "name", "period", name=op.f("uq_jobs_user_id")),
        indexes={"ix_jobs_user_name_started": ["user_id", "name", "started_at"]},
    )


def upgrade() -> None:
    """Upgrade schema."""
    _create_projects()
    _create_radar_runs()
    _create_briefs_and_jobs()


def downgrade() -> None:
    """Downgrade schema."""
    for table in DAILY_TABLES:
        op.drop_table(table)
