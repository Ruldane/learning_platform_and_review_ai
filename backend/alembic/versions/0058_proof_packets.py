"""Dossiers privés et manifestes figés des preuves choisies."""

import sqlalchemy as sa

from alembic import op

revision = "0058"
down_revision = "0057"


def upgrade() -> None:
    op.create_table(
        "proof_packets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("digest", sa.String(64), nullable=False),
        sa.Column("manifest", sa.Text(), nullable=False),
    )
    op.create_index("ix_proof_packets_user_id", "proof_packets", ["user_id"])


def downgrade() -> None:
    op.drop_table("proof_packets")
