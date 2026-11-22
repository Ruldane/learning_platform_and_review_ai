"""Défis GitHub et attributions publiques des commits du Portfolio."""

import sqlalchemy as sa

from alembic import op

revision = "0047"
down_revision = "0046"

_TABLE = "project_github_claims"


def upgrade() -> None:
    op.create_table(
        _TABLE,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("repository_id", sa.BigInteger(), nullable=False),
        sa.Column("owner", sa.String(39), nullable=False),
        sa.Column("repository", sa.String(100), nullable=False),
        sa.Column("sha", sa.String(40), nullable=False),
        sa.Column("author_id", sa.BigInteger(), nullable=False),
        sa.Column("challenge_digest", sa.String(64), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("session_id", sa.String(36), nullable=True),
    )
    op.create_index(f"ix_{_TABLE}_user_id", _TABLE, ["user_id"])
    op.create_index(f"ix_{_TABLE}_project", _TABLE, ["user_id", "project_id"])
    op.create_index(
        f"uq_{_TABLE}_confirmed_sha",
        _TABLE,
        ["user_id", "sha"],
        unique=True,
        sqlite_where=sa.text("verified_at IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_table(_TABLE)
