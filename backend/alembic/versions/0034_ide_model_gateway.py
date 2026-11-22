"""Budget de la passerelle de modèles de l’IDE, par compte et par jour."""

import sqlalchemy as sa

from alembic import op

revision = "0034"
down_revision = "0033"


def upgrade() -> None:
    op.create_table(
        "ide_gateway_budgets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("day", sa.String(10), nullable=False),
        sa.Column("reserved", sa.Integer(), nullable=False),
        sa.UniqueConstraint("user_id", "day"),
    )
    op.create_index("ix_ide_gateway_budgets_user_id", "ide_gateway_budgets", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_ide_gateway_budgets_user_id", table_name="ide_gateway_budgets")
    op.drop_table("ide_gateway_budgets")
