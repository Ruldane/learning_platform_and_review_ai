"""Onglets ouverts et fichier actif d'une séance IDE."""

import sqlalchemy as sa

from alembic import op

revision = "0032"
down_revision = "0031"


def upgrade() -> None:
    op.add_column("ide_sessions", sa.Column("workspace_tabs", sa.JSON()))


def downgrade() -> None:
    op.drop_column("ide_sessions", "workspace_tabs")
