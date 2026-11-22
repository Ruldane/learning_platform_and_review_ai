"""Dossiers de recrutement simulé et résultats par étape."""

import sqlalchemy as sa

from alembic import op

revision = "0063"
down_revision = "0061c"


def upgrade() -> None:
    op.create_table(
        "recruitment_processes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("posting_id", sa.String(36), nullable=False),
        sa.Column("offer", sa.JSON(), nullable=False),
        sa.Column("project", sa.JSON()),
        sa.Column("rubric", sa.JSON(), nullable=False),
        sa.Column("missing_proofs", sa.JSON(), nullable=False),
        sa.Column("steps", sa.JSON(), nullable=False),
    )
    op.create_index("ix_recruitment_processes_user_id", "recruitment_processes", ["user_id"])


def downgrade() -> None:
    op.drop_table("recruitment_processes")
