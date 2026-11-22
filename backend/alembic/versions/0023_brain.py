"""Dossiers, inventaire local et identité de synchronisation Cerveau."""

import sqlalchemy as sa

from alembic import op

revision = "0023"
down_revision = "0022"


def _common() -> tuple[sa.Column, ...]:
    return (
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def upgrade() -> None:
    op.add_column("documents", sa.Column("sync_metadata", sa.JSON()))
    op.create_table(
        "brain_folders",
        *_common(),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("path", sa.Text, nullable=False),
        sa.Column("paused", sa.Boolean, nullable=False),
        sa.Column("revision", sa.Integer, nullable=False),
        sa.Column("report", sa.JSON),
        sa.UniqueConstraint("user_id", "path"),
    )
    op.create_table(
        "brain_files",
        *_common(),
        sa.Column(
            "folder_id",
            sa.String(36),
            sa.ForeignKey("brain_folders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            sa.String(36),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("path", sa.Text, nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("size", sa.Integer, nullable=False),
        sa.UniqueConstraint("folder_id", "path"),
    )
    op.create_table(
        "brain_sync_tokens",
        *_common(),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.UniqueConstraint("user_id"),
    )
    for table in ("brain_folders", "brain_files", "brain_sync_tokens"):
        op.create_index(f"ix_{table}_user_id", table, ["user_id"])


def downgrade() -> None:
    for table in ("brain_sync_tokens", "brain_files", "brain_folders"):
        op.drop_table(table)
    op.drop_column("documents", "sync_metadata")
