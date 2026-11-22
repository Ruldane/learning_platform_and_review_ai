"""Propositions LinkedIn contrôlées contre le profil maître."""

import sqlalchemy as sa

from alembic import op

revision = "0048"
down_revision = "0047"


def upgrade() -> None:
    op.create_table(
        "linkedin_drafts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("profile_version", sa.Integer(), nullable=False),
        sa.Column("posting_id", sa.String(36)),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("text", sa.JSON()),
        sa.Column("revision", sa.Integer(), nullable=False),
    )
    op.create_index("ix_linkedin_drafts_user_created", "linkedin_drafts", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_table("linkedin_drafts")
