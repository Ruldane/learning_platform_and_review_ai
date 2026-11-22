"""Garde le bilan Feynman des tours de conversation."""

import sqlalchemy as sa

from alembic import op

revision = "0046"
down_revision = "0045"


def upgrade() -> None:
    op.add_column("conversation_turns", sa.Column("feynman", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("conversation_turns") as batch:
        batch.drop_column("feynman")
