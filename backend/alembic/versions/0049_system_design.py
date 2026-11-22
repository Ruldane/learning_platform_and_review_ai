"""Scènes versionnées et remise de l’entretien d’architecture."""

import sqlalchemy as sa

from alembic import op

revision = "0049"
down_revision = "0048"


def upgrade() -> None:
    op.add_column("interviews", sa.Column("system_design", sa.JSON(), nullable=True))
    op.create_table(
        "design_board_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column(
            "interview_id",
            sa.String(36),
            sa.ForeignKey("interviews.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("parent_id", sa.String(36), nullable=True),
        sa.Column("step", sa.Integer(), nullable=False),
        sa.Column("scene", sa.JSON(), nullable=False),
        sa.UniqueConstraint("interview_id", "step"),
    )
    op.create_index("ix_design_board_versions_user_id", "design_board_versions", ["user_id"])


def downgrade() -> None:
    op.drop_table("design_board_versions")
    with op.batch_alter_table("interviews") as batch:
        batch.drop_column("system_design")
