"""Exercices de transfert privés et bilan daté par compétence."""

import sqlalchemy as sa

from alembic import op

revision = "0056"
down_revision = "0055"


def upgrade() -> None:
    op.create_table(
        "skill_transfers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "skill_id",
            sa.String(36),
            sa.ForeignKey("skills.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("proof_id", sa.String(64), nullable=False),
        sa.Column("proof", sa.JSON(), nullable=False),
        sa.Column("due_on", sa.Date(), nullable=False),
        sa.Column("stage", sa.String(12), nullable=False),
        sa.Column("session_id", sa.String(36)),
        sa.Column("exercise", sa.JSON()),
        sa.Column("answer", sa.Text()),
        sa.Column("assessment", sa.JSON()),
        sa.Column("assessed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("user_id", "skill_id", "proof_id", "due_on"),
    )
    op.create_index("ix_skill_transfers_user_id", "skill_transfers", ["user_id"])


def downgrade() -> None:
    op.drop_table("skill_transfers")
