"""Les trois prises de parole d'un tour de classe virtuelle."""

import sqlalchemy as sa

from alembic import op

revision = "0030"
down_revision = "0029"


def upgrade() -> None:
    op.add_column("conversation_turns", sa.Column("classmates", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("conversation_turns", "classmates")
