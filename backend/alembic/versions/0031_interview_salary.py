"""Fourchette du radar figée lors d'une négociation de salaire."""

import sqlalchemy as sa

from alembic import op

revision = "0031"
down_revision = "0030"


def upgrade() -> None:
    op.add_column("interviews", sa.Column("salary", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("interviews", "salary")
