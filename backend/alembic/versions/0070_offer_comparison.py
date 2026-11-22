"""Critères privés du compte et comparaisons figées."""

import sqlalchemy as sa

from alembic import op

revision = "0070"
down_revision = "0069"


def upgrade() -> None:
    op.create_table(
        "offer_comparison_preferences",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("preferences", sa.JSON(), nullable=False),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(
        "ix_offer_comparison_preferences_user_id", "offer_comparison_preferences", ["user_id"]
    )
    op.create_table(
        "offer_comparisons",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
    )
    op.create_index("ix_offer_comparisons_user_id", "offer_comparisons", ["user_id"])


def downgrade() -> None:
    op.drop_table("offer_comparisons")
    op.drop_table("offer_comparison_preferences")
