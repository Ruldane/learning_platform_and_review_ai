"""IDE Python et serveur MCP : exercices, séances, exécutions, notes, préférences ; jetons,
interrupteur, journal, historique des changements et demandes à confirmer

Revision ID: 0016
Revises: 0015
Create Date: 2026-11-17 10:45:00.000000

"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0016"
down_revision: str | Sequence[str] | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_TABLES = (
    "mcp_confirmations",
    "mcp_changes",
    "mcp_calls",
    "mcp_prefs",
    "mcp_tokens",
    "ide_preferences",
    "ide_notes",
    "ide_runs",
    "ide_sessions",
    "ide_exercises",
)


def _s(name: str, length: int, null: bool = False) -> sa.Column[Any]:
    return sa.Column(name, sa.String(length=length), nullable=null)


def _t(name: str, null: bool = False) -> sa.Column[Any]:
    return sa.Column(name, sa.Text(), nullable=null)


def _i(name: str, null: bool = False) -> sa.Column[Any]:
    return sa.Column(name, sa.Integer(), nullable=null)


def _b(name: str) -> sa.Column[Any]:
    return sa.Column(name, sa.Boolean(), nullable=False)


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


def _create_ide_content() -> None:
    _create(
        "ide_exercises",
        _s("title", 120),
        _t("statement"),
        _j("files"),
        _s("entry", 200),
        _s("origin", 16),
        _s("topic", 300, True),
        _s("session_id", 36, True),
    )
    _create(
        "ide_sessions",
        _s("exercise_id", 36, True),
        _s("title", 120),
        _j("files"),
        _s("entry", 200),
        _i("teacher_tokens"),
        _dt("passed_at", True),
        indexes={"ix_ide_sessions_user_updated": ["user_id", "updated_at"]},
    )
    _create(
        "ide_preferences",
        _s("teacher_mode", 16),
        _b("idle_trigger"),
        _i("session_cap"),
        _i("day_cap"),
        sa.UniqueConstraint("user_id", name=op.f("uq_ide_preferences_user_id")),
    )


def _create_ide_runs_and_notes() -> None:
    _create(
        "ide_runs",
        _s("session_id", 36),
        _s("kind", 8),
        _s("entry", 200),
        _s("status", 16),
        _i("exit_code", True),
        _i("duration_ms", True),
        _b("truncated"),
        _t("output"),
        _s("requested_by", 60),
        _s("error_signature", 40, True),
        indexes={"ix_ide_runs_session": ["session_id", "created_at"]},
    )
    _create(
        "ide_notes",
        _s("session_id", 36),
        _s("kind", 16),
        _s("author", 16),
        _s("author_label", 60, True),
        _s("status", 16),
        _s("file_path", 200, True),
        _i("line_start", True),
        _i("line_end", True),
        _t("content"),
        _t("replacement", True),
        _s("base_hash", 64, True),
        _s("reference_note_id", 36, True),
        _s("error_key", 64, True),
        indexes={"ix_ide_notes_session": ["session_id", "created_at"]},
    )


def _create_mcp_access() -> None:
    _create(
        "mcp_tokens",
        _s("label", 60),
        _s("hash", 64),
        _j("features"),
        _s("mode", 8),
        _dt("expires_at"),
        _dt("revoked_at", True),
        _dt("last_used_at", True),
        sa.UniqueConstraint("hash", name=op.f("uq_mcp_tokens_hash")),
    )
    _create(
        "mcp_prefs",
        _b("enabled"),
        sa.UniqueConstraint("user_id", name=op.f("uq_mcp_prefs_user_id")),
    )


def _create_mcp_journal() -> None:
    _create(
        "mcp_calls",
        _s("token_id", 36, True),
        _s("action", 80),
        _i("level"),
        _i("code"),
        _i("duration_ms"),
        _j("ids"),
        indexes={
            "ix_mcp_calls_token_id": ["token_id"],
            "ix_mcp_calls_user_created": ["user_id", "created_at"],
        },
    )
    _create(
        "mcp_changes",
        _s("call_id", 36),
        _s("table_name", 64),
        _s("row_id", 36),
        _s("op", 8),
        _j("before", True),
        _j("after", True),
        _dt("undone_at", True),
        indexes={"ix_mcp_changes_call": ["call_id"]},
    )
    _create(
        "mcp_confirmations",
        _s("token_id", 36),
        _s("action", 80),
        _j("request"),
        _t("summary"),
        _j("precheck", True),
        _s("status", 16),
        _dt("expires_at"),
        _dt("decided_at", True),
        _i("result_code", True),
        indexes={
            "ix_mcp_confirmations_token_id": ["token_id"],
            "ix_mcp_confirmations_user_status": ["user_id", "status"],
        },
    )


def upgrade() -> None:
    """Upgrade schema."""
    _create_ide_content()
    _create_ide_runs_and_notes()
    _create_mcp_access()
    _create_mcp_journal()


def downgrade() -> None:
    """Downgrade schema."""
    for table in NEW_TABLES:
        op.drop_table(table)
