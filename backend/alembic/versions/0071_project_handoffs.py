"""Guides privés de reprise approuvés à partir d'un rendu de projet."""

import sqlalchemy as sa

from alembic import op

revision = "0071"
down_revision = "0070"


def upgrade() -> None:
    op.create_table(
        "project_handoffs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("project_title", sa.String(200), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("digest", sa.String(64), nullable=False),
        sa.Column("markdown", sa.Text(), nullable=False),
    )
    op.create_index("ix_project_handoffs_user_id", "project_handoffs", ["user_id"])


def downgrade() -> None:
    op.drop_table("project_handoffs")
