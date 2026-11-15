"""reminders.postponed : une relance reportée par January ne suit plus les délais (D140)

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-15 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0012"
down_revision: str | Sequence[str] | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("reminders", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("postponed", sa.Boolean(), nullable=False, server_default=sa.false())
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("reminders", schema=None) as batch_op:
        batch_op.drop_column("postponed")
