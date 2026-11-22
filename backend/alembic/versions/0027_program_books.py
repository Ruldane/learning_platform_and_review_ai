"""Éditions PDF et EPUB des programmes."""

import sqlalchemy as sa

from alembic import op

revision = "0027"
down_revision = "0026"


def upgrade() -> None:
    op.create_table(
        "program_books",
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
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("source_hash", sa.String(64)),
        sa.Column("pdf_key", sa.String(200)),
        sa.Column("epub_key", sa.String(200)),
        sa.Column("chapters", sa.Integer(), nullable=False),
        sa.Column("rendered_at", sa.DateTime(timezone=True)),
        sa.Column("failed", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("user_id", "program_id"),
    )
    op.create_index("ix_program_books_user_id", "program_books", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_program_books_user_id", table_name="program_books")
    op.drop_table("program_books")
