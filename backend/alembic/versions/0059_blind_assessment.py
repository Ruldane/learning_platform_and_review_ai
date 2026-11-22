"""Épreuves et grilles de comparaison à l’aveugle."""

import sqlalchemy as sa

from alembic import op

revision = "0059"
down_revision = "0058b"


def upgrade() -> None:
    op.create_table(
        "blind_assessments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rubric", sa.JSON(), nullable=False),
        sa.Column("source_a", sa.JSON(), nullable=False),
        sa.Column("source_b", sa.JSON(), nullable=False),
        sa.Column("stage", sa.String(12), nullable=False),
        sa.Column("session_id", sa.String(36)),
        sa.Column("grade", sa.JSON()),
        sa.Column("evaluated_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_blind_assessments_user_id", "blind_assessments", ["user_id"])


def downgrade() -> None:
    op.drop_table("blind_assessments")
