"""Reçus de révisions effectuées hors connexion."""

import sqlalchemy as sa

from alembic import op

revision = "0051"
down_revision = "0050"


def upgrade() -> None:
    op.create_table(
        "offline_reviews",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("receipt_id", sa.String(36), nullable=False),
        sa.Column("card_id", sa.String(36), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("ok", sa.Boolean(), nullable=False),
        sa.Column("response", sa.JSON()),
        sa.UniqueConstraint("user_id", "receipt_id"),
    )


def downgrade() -> None:
    op.drop_table("offline_reviews")
