"""Dossiers de contribution open source."""

import sqlalchemy as sa

from alembic import op

revision = "0029"
down_revision = "0028"


def upgrade() -> None:
    op.create_table(
        "contributions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "program_id",
            sa.String(36),
            sa.ForeignKey("programs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chapter_id", sa.String(36), nullable=False),
        sa.Column("chapter_title", sa.String(200), nullable=False),
        sa.Column("repository", sa.String(140), nullable=False),
        sa.Column("issue_number", sa.Integer(), nullable=False),
        sa.Column("issue_title", sa.String(200), nullable=False),
        sa.Column("issue_body", sa.Text(), nullable=False),
        sa.Column("skills", sa.JSON(), nullable=False),
        sa.Column("base", sa.String(100), nullable=False),
        sa.Column("marker", sa.String(36), nullable=False),
        sa.Column("publication", sa.JSON()),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("pull_number", sa.Integer()),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.UniqueConstraint("user_id", "repository", "issue_number"),
    )
    op.create_index("ix_contributions_user_id", "contributions", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_contributions_user_id", table_name="contributions")
    op.drop_table("contributions")
