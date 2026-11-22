"""Instantanés, plaidoiries et verdicts du procès du code."""

import sqlalchemy as sa

from alembic import op

revision = "0037"
down_revision = "0036"


def upgrade() -> None:
    op.create_table(
        "code_trials",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "ide_session_id",
            sa.String(36),
            sa.ForeignKey("ide_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("files_version", sa.Integer(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("pleadings", sa.JSON(none_as_null=True)),
        sa.Column("verdict_choice", sa.String(16)),
        sa.Column("verdict_reason", sa.String(2000)),
        sa.UniqueConstraint("user_id", "ide_session_id", "files_version"),
    )
    op.create_index("ix_code_trials_user_id", "code_trials", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_code_trials_user_id", table_name="code_trials")
    op.drop_table("code_trials")
