"""candidatures (fiches, fil, contacts, relances, kit, entretiens, comité), dossier d'entreprise

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-15 12:00:00.000000

"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0011"
down_revision: str | Sequence[str] | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Enfants avant parents (clés étrangères) ; les index suivent leur table.
APPLICATION_TABLES = (
    "committee_runs",
    "interviews",
    "kit_items",
    "reminders",
    "contacts",
    "application_events",
    "applications",
)


def _s(name: str, length: int, null: bool = False) -> sa.Column[Any]:
    return sa.Column(name, sa.String(length=length), nullable=null)


def _t(name: str, null: bool = False) -> sa.Column[Any]:
    return sa.Column(name, sa.Text(), nullable=null)


def _i(name: str) -> sa.Column[Any]:
    return sa.Column(name, sa.Integer(), nullable=False)


def _d(name: str, null: bool = False) -> sa.Column[Any]:
    return sa.Column(name, sa.Date(), nullable=null)


def _j(name: str, null: bool = False) -> sa.Column[Any]:
    return sa.Column(name, sa.JSON(), nullable=null)


def _dt(name: str, null: bool = False) -> sa.Column[Any]:
    return sa.Column(name, sa.DateTime(timezone=True), nullable=null)


def _fk(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["application_id"],
        ["applications.id"],
        name=op.f(f"fk_{table}_application_id_applications"),
        ondelete="CASCADE",
    )


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


def _create_applications() -> None:
    _create(
        "applications",
        _s("posting_id", 36, True),
        _s("company", 200),
        _s("company_norm", 200),
        _s("title", 200),
        _t("url", True),
        _s("url_norm", 2048, True),
        _t("posting_text", True),
        _s("channel", 16, True),
        _s("status", 16),
        _d("applied_on", True),
        _d("interview_on", True),
        _d("answered_on", True),
        _s("cv_version_id", 36, True),
        _t("letter", True),
        _t("notes", True),
        _s("next_action", 200, True),
        _d("next_action_on", True),
        _j("distinct_from"),
        indexes={
            "ix_applications_url": ["user_id", "url_norm"],
            "ix_applications_company": ["user_id", "company_norm"],
            "ix_applications_posting": ["user_id", "posting_id"],
        },
    )
    _create(
        "application_events",
        _s("application_id", 36),
        _s("kind", 16),
        _dt("at"),
        _s("status_from", 16, True),
        _s("status_to", 16, True),
        _t("text", True),
        _s("ref_id", 36, True),
        _fk("application_events"),
        indexes={"ix_application_events_application_id": ["application_id"]},
    )
    _create(
        "contacts",
        _s("application_id", 36),
        _s("name", 120),
        _s("role", 120, True),
        _s("url", 500, True),
        _fk("contacts"),
        indexes={"ix_contacts_application_id": ["application_id"]},
    )


def _create_follow_up() -> None:
    _create(
        "reminders",
        _s("application_id", 36),
        _s("kind", 16),
        _d("anchor_on"),
        _d("due_on"),
        _s("status", 16),
        _dt("done_at", True),
        _fk("reminders"),
        sa.UniqueConstraint(
            "application_id", "kind", "anchor_on", name=op.f("uq_reminders_application_id")
        ),
        indexes={"ix_reminders_due_on_status": ["due_on", "status"]},
    )
    _create(
        "kit_items",
        _s("application_id", 36),
        _s("kind", 16),
        _s("status", 16),
        _t("content"),
        _j("meta"),
        sa.Column("edited", sa.Boolean(), nullable=False),
        _s("session_id", 36, True),
        _fk("kit_items"),
        sa.UniqueConstraint("application_id", "kind", name=op.f("uq_kit_items_application_id")),
    )


def _create_practice() -> None:
    _create(
        "interviews",
        _s("application_id", 36, True),
        _s("posting_id", 36, True),
        _s("role", 200, True),
        _s("mode", 16),
        _i("duration_min"),
        _s("language", 2),
        _s("session_id", 36),
        _s("status", 16),
        _j("exchanges"),
        _j("debrief", True),
        indexes={"ix_interviews_application": ["user_id", "application_id"]},
    )
    _create(
        "committee_runs",
        _s("cv_version_id", 36),
        _s("posting_id", 36),
        _s("application_id", 36, True),
        _s("session_id", 36),
        _s("status", 16),
        _j("votes"),
        _s("verdict", 40, True),
        _j("objections"),
        _j("changes"),
        _s("previous_id", 36, True),
        indexes={"ix_committee_runs_cv_version": ["user_id", "cv_version_id"]},
    )


def upgrade() -> None:
    """Upgrade schema."""
    _create_applications()
    _create_follow_up()
    _create_practice()
    with op.batch_alter_table("companies", schema=None) as batch_op:
        batch_op.add_column(sa.Column("dossier", sa.JSON(), nullable=True))
        batch_op.add_column(
            sa.Column("dossier_sources", sa.JSON(), nullable=False, server_default="[]")
        )
        batch_op.add_column(sa.Column("dossier_at", sa.DateTime(timezone=True), nullable=True))
    with op.batch_alter_table("flashcards", schema=None) as batch_op:
        batch_op.alter_column(
            "source",
            existing_type=sa.String(length=8),
            type_=sa.String(length=16),
            existing_nullable=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("flashcards", schema=None) as batch_op:
        batch_op.alter_column(
            "source",
            existing_type=sa.String(length=16),
            type_=sa.String(length=8),
            existing_nullable=False,
        )
    with op.batch_alter_table("companies", schema=None) as batch_op:
        batch_op.drop_column("dossier_at")
        batch_op.drop_column("dossier_sources")
        batch_op.drop_column("dossier")
    for table in APPLICATION_TABLES:
        op.drop_table(table)
