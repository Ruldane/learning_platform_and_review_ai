"""Repère facultatif du Tuteur sur une réponse à un exercice du training."""

import sqlalchemy as sa

from alembic import op

revision = "0045"
down_revision = "0044"


def upgrade() -> None:
    op.add_column("conversation_turns", sa.Column("focus_outcome", sa.String(7)))


def downgrade() -> None:
    op.drop_column("conversation_turns", "focus_outcome")
