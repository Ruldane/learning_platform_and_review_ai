"""Hypothèses de prérequis, erreurs référencées et exercices correctifs."""

import sqlalchemy as sa

from alembic import op

revision = "0057"
down_revision = "0056"


def _owned_columns() -> list[sa.Column[object]]:
    return [
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "atlas_hypotheses",
        *_owned_columns(),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("label_key", sa.String(64), nullable=False),
        sa.Column("exercise", sa.JSON(), nullable=True),
        sa.UniqueConstraint("user_id", "label_key"),
    )
    op.create_index("ix_atlas_hypotheses_user_id", "atlas_hypotheses", ["user_id"])
    op.create_table(
        "atlas_observations",
        *_owned_columns(),
        sa.Column(
            "hypothesis_id",
            sa.String(36),
            sa.ForeignKey("atlas_hypotheses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("evidence_key", sa.String(64), nullable=False),
        sa.Column("confidence", sa.String(8), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.UniqueConstraint("user_id", "hypothesis_id", "evidence_key"),
    )
    op.create_index("ix_atlas_observations_user_id", "atlas_observations", ["user_id"])


def downgrade() -> None:
    op.drop_table("atlas_observations")
    op.drop_table("atlas_hypotheses")
