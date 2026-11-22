"""Chronologies d’incident et hypothèses privées."""

import sqlalchemy as sa

from alembic import op

revision = "0061a"
down_revision = "0061"


def upgrade() -> None:
    op.create_table(
        "incident_replays",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("receipt", sa.String(36), nullable=False),
        sa.Column("scenario", sa.String(48), nullable=False),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("timeline", sa.JSON(), nullable=False),
        sa.Column("notes", sa.JSON(), nullable=False),
        sa.UniqueConstraint("user_id", "receipt"),
    )
    op.create_index("ix_incident_replays_user_id", "incident_replays", ["user_id"])


def downgrade() -> None:
    op.drop_table("incident_replays")
