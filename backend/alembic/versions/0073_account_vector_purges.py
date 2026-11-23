"""Reprise durable de la purge des vecteurs après l'effacement d'un compte Google."""

import sqlalchemy as sa

from alembic import op

revision = "0073"
down_revision = "0072"


def upgrade() -> None:
    op.create_table(
        "account_vector_purges",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", name="uq_account_vector_purges_user_id"),
    )
    op.create_index("ix_account_vector_purges_user_id", "account_vector_purges", ["user_id"])


def downgrade() -> None:
    op.drop_table("account_vector_purges")
