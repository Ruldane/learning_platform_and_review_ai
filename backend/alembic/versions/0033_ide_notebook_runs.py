"""Origine et empreinte de la cellule exécutée dans le bac."""

import sqlalchemy as sa

from alembic import op

revision = "0033"
down_revision = "0032"


def upgrade() -> None:
    op.add_column("ide_runs", sa.Column("notebook_cell", sa.JSON()))


def downgrade() -> None:
    op.drop_column("ide_runs", "notebook_cell")
