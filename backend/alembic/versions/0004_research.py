"""research

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-12 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _base_columns() -> list[sa.Column]:  # type: ignore[type-arg]
    return [
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def _create_web_cache() -> None:
    op.create_table(
        "web_cache",
        sa.Column("kind", sa.String(length=8), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        *_base_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_web_cache")),
        sa.UniqueConstraint("user_id", "kind", "key_hash", name=op.f("uq_web_cache_user_id")),
    )
    with op.batch_alter_table("web_cache", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_web_cache_user_id"), ["user_id"], unique=False)


def _create_sources() -> None:
    op.create_table(
        "sources",
        sa.Column("session_id", sa.String(length=36), nullable=True),
        sa.Column("kind", sa.String(length=8), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("url_hash", sa.String(length=64), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("author", sa.Text(), nullable=True),
        sa.Column("lang", sa.String(length=8), nullable=True),
        sa.Column("published", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("verdict", sa.String(length=16), nullable=False),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("score_detail", sa.JSON(), nullable=True),
        sa.Column("reason", sa.String(length=300), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        *_base_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sources")),
        sa.UniqueConstraint("user_id", "session_id", "url_hash", name=op.f("uq_sources_user_id")),
    )
    with op.batch_alter_table("sources", schema=None) as batch_op:
        batch_op.create_index("ix_sources_user_session", ["user_id", "session_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_sources_user_id"), ["user_id"], unique=False)


def _create_web_queries() -> None:
    op.create_table(
        "web_queries",
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("query_hash", sa.String(length=64), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("lang", sa.String(length=8), nullable=True),
        sa.Column("provider", sa.String(length=16), nullable=True),
        sa.Column("result_count", sa.Integer(), nullable=False),
        *_base_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_web_queries")),
        sa.UniqueConstraint(
            "user_id", "session_id", "query_hash", name=op.f("uq_web_queries_user_id")
        ),
    )
    with op.batch_alter_table("web_queries", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_web_queries_user_id"), ["user_id"], unique=False)


def _create_search_usage() -> None:
    op.create_table(
        "search_usage",
        sa.Column("provider", sa.String(length=16), nullable=False),
        sa.Column("month", sa.String(length=7), nullable=False),
        sa.Column("key_fingerprint", sa.String(length=16), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        *_base_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_search_usage")),
        sa.UniqueConstraint(
            "user_id", "provider", "month", "key_fingerprint", name=op.f("uq_search_usage_user_id")
        ),
    )
    with op.batch_alter_table("search_usage", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_search_usage_user_id"), ["user_id"], unique=False)


def upgrade() -> None:
    """Upgrade schema."""
    _create_web_cache()
    _create_sources()
    _create_web_queries()
    _create_search_usage()


def downgrade() -> None:
    """Downgrade schema."""
    # Aucune clé étrangère entre ces tables ; les index suivent la table.
    op.drop_table("search_usage")
    op.drop_table("web_queries")
    op.drop_table("sources")
    op.drop_table("web_cache")
