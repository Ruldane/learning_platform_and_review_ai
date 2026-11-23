"""Préférences du Labo, filtres des dossiers et activité du relais Cerveau."""

import sqlalchemy as sa

from alembic import op

revision = "0072"
down_revision = "0071a"


def upgrade() -> None:
    op.create_table(
        "lab_preferences",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("pinned", sa.JSON(), nullable=False),
        sa.Column("tour", sa.String(10), nullable=False),
        sa.UniqueConstraint("user_id", name="uq_lab_preferences_user_id"),
    )
    op.create_index("ix_lab_preferences_user_id", "lab_preferences", ["user_id"])
    for name in ("excluded_directories", "excluded_extensions"):
        op.add_column(
            "brain_folders", sa.Column(name, sa.JSON(), nullable=False, server_default="[]")
        )
    op.add_column("brain_sync_tokens", sa.Column("last_contact", sa.DateTime(timezone=True)))


def downgrade() -> None:
    with op.batch_alter_table("brain_sync_tokens") as batch:
        batch.drop_column("last_contact")
    with op.batch_alter_table("brain_folders") as batch:
        batch.drop_column("excluded_extensions")
        batch.drop_column("excluded_directories")
    op.drop_table("lab_preferences")
