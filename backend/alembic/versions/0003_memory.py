"""memory

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-11 15:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _base_columns() -> list[sa.Column]:  # type: ignore[type-arg]
    return [
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def _create_memory_items() -> None:
    op.create_table(
        "memory_items",
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=True),
        sa.Column("source_id", sa.String(length=36), nullable=True),
        sa.Column("lang", sa.String(length=8), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
        *_base_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_memory_items")),
        sa.UniqueConstraint("user_id", "content_hash", name=op.f("uq_memory_items_user_id")),
    )
    with op.batch_alter_table("memory_items", schema=None) as batch_op:
        batch_op.create_index("ix_memory_items_user_kind", ["user_id", "kind"], unique=False)
        batch_op.create_index("ix_memory_items_user_status", ["user_id", "status"], unique=False)
        batch_op.create_index(batch_op.f("ix_memory_items_user_id"), ["user_id"], unique=False)


def _create_documents() -> None:
    op.create_table(
        "documents",
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("source_kind", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("storage_key", sa.String(length=200), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("source_hash", sa.String(length=64), nullable=False),
        sa.Column("item_id", sa.String(length=36), nullable=True),
        sa.Column("learned", sa.Boolean(), nullable=False),
        sa.Column("error", sa.JSON(), nullable=True),
        *_base_columns(),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["memory_items.id"],
            name=op.f("fk_documents_item_id_memory_items"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_documents")),
        sa.UniqueConstraint("user_id", "source_hash", name=op.f("uq_documents_user_id")),
    )
    with op.batch_alter_table("documents", schema=None) as batch_op:
        batch_op.create_index("ix_documents_user_status", ["user_id", "status"], unique=False)
        batch_op.create_index(batch_op.f("ix_documents_user_id"), ["user_id"], unique=False)


def _create_memory_chunks() -> None:
    op.create_table(
        "memory_chunks",
        sa.Column("item_id", sa.String(length=36), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        *_base_columns(),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["memory_items.id"],
            name=op.f("fk_memory_chunks_item_id_memory_items"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_memory_chunks")),
        sa.UniqueConstraint("item_id", "ordinal", name=op.f("uq_memory_chunks_item_id")),
    )
    with op.batch_alter_table("memory_chunks", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_memory_chunks_user_id"), ["user_id"], unique=False)


def _create_memory_writes() -> None:
    op.create_table(
        "memory_writes",
        sa.Column("item_id", sa.String(length=36), nullable=False),
        sa.Column("item_title", sa.String(length=200), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("author", sa.String(length=64), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=True),
        sa.Column("reason", sa.String(length=300), nullable=True),
        *_base_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_memory_writes")),
    )
    with op.batch_alter_table("memory_writes", schema=None) as batch_op:
        batch_op.create_index("ix_memory_writes_user_item", ["user_id", "item_id"], unique=False)
        batch_op.create_index(
            "ix_memory_writes_user_created", ["user_id", "created_at"], unique=False
        )
        batch_op.create_index(batch_op.f("ix_memory_writes_user_id"), ["user_id"], unique=False)


def upgrade() -> None:
    """Upgrade schema."""
    # `memory_items` d'abord : `documents` et `memory_chunks` y renvoient.
    _create_memory_items()
    _create_documents()
    _create_memory_chunks()
    _create_memory_writes()


def downgrade() -> None:
    """Downgrade schema."""
    # Les tables qui renvoient à `memory_items` partent avant elle ; les index suivent la table.
    op.drop_table("memory_writes")
    op.drop_table("memory_chunks")
    op.drop_table("documents")
    op.drop_table("memory_items")
