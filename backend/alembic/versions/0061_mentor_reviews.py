"""Copies figées accessibles par jeton temporaire et commentaires des mentors."""

import sqlalchemy as sa

from alembic import op

revision = "0061"
down_revision = "0060"


def upgrade() -> None:
    op.create_table(
        "mentor_shares",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("packet_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("digest", sa.String(64), nullable=False),
        sa.Column("manifest", sa.Text(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_mentor_shares_user_id", "mentor_shares", ["user_id"])
    op.create_table(
        "mentor_comments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "share_id",
            sa.String(36),
            sa.ForeignKey("mentor_shares.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("proof_id", sa.String(36), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("reviewed", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_mentor_comments_user_id", "mentor_comments", ["user_id"])
    op.create_index("ix_mentor_comments_share_id", "mentor_comments", ["share_id"])


def downgrade() -> None:
    op.drop_table("mentor_comments")
    op.drop_table("mentor_shares")
