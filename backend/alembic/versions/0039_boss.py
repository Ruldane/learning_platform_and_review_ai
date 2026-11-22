"""Tentative du Boss, calendrier côté serveur, instantané et évaluation."""

import sqlalchemy as sa

from alembic import op

revision = "0039"
down_revision = "0038"


def upgrade() -> None:
    op.create_table(
        "boss_attempts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("program_id", sa.String(36), nullable=False),
        sa.Column("ide_session_id", sa.String(36), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("change_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("brief", sa.Text(), nullable=False),
        sa.Column("change", sa.Text(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("submitted_files", sa.JSON()),
        sa.Column("sandbox_run_id", sa.String(36)),
        sa.Column("review_session_id", sa.String(36)),
        sa.Column("diagnostic", sa.JSON()),
        sa.Column("verdict", sa.JSON()),
        sa.Column("proof_recorded", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["program_id"], ["programs.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "program_id"),
    )
    op.create_index("ix_boss_attempts_user_id", "boss_attempts", ["user_id"])


def downgrade() -> None:
    op.drop_table("boss_attempts")
