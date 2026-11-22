"""Prises de parole sourcées et jugement sur un tour de débat."""

import sqlalchemy as sa

from alembic import op

revision = "0044"
down_revision = "0043"


def upgrade() -> None:
    op.add_column("conversation_turns", sa.Column("expert_speeches", sa.JSON(), nullable=True))
    op.add_column("conversation_turns", sa.Column("expert_judgment", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("conversation_turns") as batch:
        batch.drop_column("expert_judgment")
        batch.drop_column("expert_speeches")
