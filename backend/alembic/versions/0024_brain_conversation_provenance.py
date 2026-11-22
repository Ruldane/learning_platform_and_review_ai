"""Versions de notes synchronisées effectivement utilisées dans chaque tour du Cerveau."""

import sqlalchemy as sa

from alembic import op

revision = "0024"
down_revision = "0023"


def upgrade() -> None:
    op.add_column("conversation_turns", sa.Column("context_notes", sa.JSON))


def downgrade() -> None:
    op.drop_column("conversation_turns", "context_notes")
