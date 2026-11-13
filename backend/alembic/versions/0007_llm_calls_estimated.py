"""llm_calls.estimated : tokens estimés d'un appel coupé (D117)

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-13 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("llm_calls", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("estimated", sa.Boolean(), nullable=False, server_default="0")
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("llm_calls", schema=None) as batch_op:
        batch_op.drop_column("estimated")
