"""Versions privées et site portfolio approuvé."""

import sqlalchemy as sa

from alembic import op

revision = "0052"
down_revision = "0051"


def _columns() -> tuple[sa.Column[str], sa.Column[str], sa.Column[object], sa.Column[object]]:
    return (
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def upgrade() -> None:
    op.create_table(
        "portfolio_drafts",
        *_columns(),
        sa.Column("digest", sa.String(64), nullable=False),
        sa.Column("html_key", sa.String(), nullable=False),
        sa.Column("zip_key", sa.String(), nullable=False),
    )
    op.create_index("ix_portfolio_drafts_user_id", "portfolio_drafts", ["user_id"])
    op.create_table(
        "portfolio_sites",
        *_columns(),
        sa.Column("slug", sa.String(200), nullable=False),
        sa.Column(
            "draft_id", sa.String(36), sa.ForeignKey("portfolio_drafts.id", ondelete="SET NULL")
        ),
        sa.Column(
            "published_id", sa.String(36), sa.ForeignKey("portfolio_drafts.id", ondelete="SET NULL")
        ),
        sa.Column("published_url", sa.String(300)),
        sa.Column("published_at", sa.DateTime()),
        sa.Column("use_in_cv", sa.Boolean(), nullable=False),
        sa.Column("use_in_kit", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_portfolio_sites_user_id", "portfolio_sites", ["user_id"])


def downgrade() -> None:
    op.drop_table("portfolio_sites")
    op.drop_table("portfolio_drafts")
