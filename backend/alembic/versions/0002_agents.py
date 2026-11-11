"""agents

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-11 12:17:07.919597

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _create_llm_calls() -> None:
    op.create_table(
        "llm_calls",
        sa.Column("session_id", sa.String(length=36), nullable=True),
        sa.Column("graph", sa.String(length=64), nullable=True),
        sa.Column("agent", sa.String(length=64), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("tokens_in", sa.Integer(), nullable=False),
        sa.Column("tokens_out", sa.Integer(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Double(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_llm_calls")),
    )
    with op.batch_alter_table("llm_calls", schema=None) as batch_op:
        batch_op.create_index("ix_llm_calls_user_created", ["user_id", "created_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_llm_calls_user_id"), ["user_id"], unique=False)


def _create_sessions() -> None:
    op.create_table(
        "sessions",
        sa.Column("graph", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("input", sa.JSON(), nullable=False),
        sa.Column("subject_type", sa.String(length=32), nullable=True),
        sa.Column("subject_id", sa.String(length=36), nullable=True),
        sa.Column("pending_interrupt", sa.JSON(), nullable=True),
        sa.Column("error", sa.JSON(), nullable=True),
        sa.Column("tokens_in", sa.Integer(), nullable=False),
        sa.Column("tokens_out", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Double(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sessions")),
    )
    with op.batch_alter_table("sessions", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_sessions_user_id"), ["user_id"], unique=False)
        batch_op.create_index("ix_sessions_user_status", ["user_id", "status"], unique=False)


def _create_session_events() -> None:
    op.create_table(
        "session_events",
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("agent", sa.String(length=64), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["sessions.id"],
            name=op.f("fk_session_events_session_id_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_session_events")),
        sa.UniqueConstraint("session_id", "seq", name="uq_session_events_session_seq"),
    )
    with op.batch_alter_table("session_events", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_session_events_user_id"), ["user_id"], unique=False)


def upgrade() -> None:
    """Upgrade schema."""
    _create_llm_calls()
    _create_sessions()
    _create_session_events()


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("session_events", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_session_events_user_id"))

    op.drop_table("session_events")
    with op.batch_alter_table("sessions", schema=None) as batch_op:
        batch_op.drop_index("ix_sessions_user_status")
        batch_op.drop_index(batch_op.f("ix_sessions_user_id"))

    op.drop_table("sessions")
    with op.batch_alter_table("llm_calls", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_llm_calls_user_id"))
        batch_op.drop_index("ix_llm_calls_user_created")

    op.drop_table("llm_calls")
