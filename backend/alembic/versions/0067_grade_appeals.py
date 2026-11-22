"""Contestations, remises figées et deux lectures de critères."""

import sqlalchemy as sa

from alembic import op

revision = "0067"
down_revision = "0066"


def upgrade() -> None:
    op.create_table(
        "grade_appeals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("source", sa.JSON(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("session_id", sa.String(36)),
        sa.Column("second", sa.JSON()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("decision", sa.String(20)),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_grade_appeals_user_id", "grade_appeals", ["user_id"])


def downgrade() -> None:
    op.drop_table("grade_appeals")
