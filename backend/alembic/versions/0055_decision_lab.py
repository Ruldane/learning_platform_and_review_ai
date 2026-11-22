"""Scénarios sauvegardés du laboratoire de décisions."""

import sqlalchemy as sa

from alembic import op

revision = "0055"
down_revision = "0054"


def upgrade() -> None:
    op.create_table(
        "decision_lab_scenarios",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("assumptions", sa.JSON(), nullable=False),
        sa.Column("results", sa.JSON(), nullable=False),
        sa.Column("critique", sa.Text(), nullable=False),
    )
    op.create_index("ix_decision_lab_scenarios_user_id", "decision_lab_scenarios", ["user_id"])


def downgrade() -> None:
    op.drop_table("decision_lab_scenarios")
