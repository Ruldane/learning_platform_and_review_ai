"""Jeux de données synthétiques, traces et conclusions."""

import sqlalchemy as sa

from alembic import op

revision = "0061b"
down_revision = "0061a"


def upgrade() -> None:
    op.create_table(
        "data_investigations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dataset", sa.JSON(), nullable=False),
        sa.Column("source_rows", sa.JSON(), nullable=False),
        sa.Column("source_digest", sa.String(64), nullable=False),
        sa.Column("operations", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON()),
    )
    op.create_index("ix_data_investigations_user_id", "data_investigations", ["user_id"])


def downgrade() -> None:
    op.drop_table("data_investigations")
