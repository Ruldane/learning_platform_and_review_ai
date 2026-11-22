"""Engagements datés et mesure de l’écart à la cible."""

import sqlalchemy as sa

from alembic import op

revision = "0069"
down_revision = "0067"


def upgrade() -> None:
    op.create_table(
        "dated_commitments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("version", sa.String(80), nullable=False),
        sa.Column("intention", sa.Text(), nullable=False),
        sa.Column("indicator", sa.String(160), nullable=False),
        sa.Column("unit", sa.String(40), nullable=False),
        sa.Column("target", sa.String(32), nullable=False),
        sa.Column("due_on", sa.Date(), nullable=False),
        sa.Column("observed", sa.String(32), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("reviewed_on", sa.Date(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("user_id", "request_id"),
    )
    op.create_index("ix_dated_commitments_user_id", "dated_commitments", ["user_id"])


def downgrade() -> None:
    op.drop_table("dated_commitments")
