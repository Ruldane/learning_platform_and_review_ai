"""Alerte simulée, état d'enquête, diagnostic et rapport d'astreinte."""

import sqlalchemy as sa

from alembic import op

revision = "0035"
down_revision = "0034"


def upgrade() -> None:
    op.create_table(
        "oncall_incidents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=False),
        sa.Column("alert_at", sa.Integer(), nullable=False),
        sa.Column("ide_session_id", sa.String(36), nullable=False),
        sa.Column("minute", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("events", sa.JSON(), nullable=False),
        sa.Column("observed_events", sa.JSON(), nullable=False),
        sa.Column("diagnostic_run_id", sa.String(36)),
        sa.Column("diagnostic_state", sa.String(16), nullable=False),
        sa.Column("diagnostic_hash", sa.String(64)),
        sa.Column("report", sa.Text()),
        sa.Column("review_session_id", sa.String(36)),
        sa.Column("review_context", sa.JSON()),
        sa.Column("verdict", sa.JSON()),
        sa.Column("proof_recorded", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_oncall_incidents_user_id", "oncall_incidents", ["user_id"])
    op.create_index(
        "uq_oncall_running_diagnostic",
        "oncall_incidents",
        ["user_id"],
        unique=True,
        sqlite_where=sa.text("diagnostic_state = 'running'"),
    )


def downgrade() -> None:
    op.drop_index("uq_oncall_running_diagnostic", table_name="oncall_incidents")
    op.drop_index("ix_oncall_incidents_user_id", table_name="oncall_incidents")
    op.drop_table("oncall_incidents")
