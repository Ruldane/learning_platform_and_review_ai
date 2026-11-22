"""Sources de veille et pile de lecture."""

import sqlalchemy as sa

from alembic import op

revision = "0026"
down_revision = "0025"


def upgrade() -> None:
    op.create_table(
        "reading_sources",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("kind", sa.String(12), nullable=False),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("value", sa.String(2000), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("user_id", "kind", "value"),
    )
    op.create_index("ix_reading_sources_user_id", "reading_sources", ["user_id"])
    op.create_table(
        "reading_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("kind", sa.String(12), nullable=False),
        sa.Column("url", sa.String(2000), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("summary", sa.String(600), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("reason", sa.String(240), nullable=False),
        sa.Column("company", sa.String(160)),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("user_id", "url"),
    )
    op.create_index("ix_reading_items_user_id", "reading_items", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_reading_items_user_id", table_name="reading_items")
    op.drop_table("reading_items")
    op.drop_index("ix_reading_sources_user_id", table_name="reading_sources")
    op.drop_table("reading_sources")
