"""radar_runs.error_code : le code lisible d'un relevé en échec (D160)

Revision ID: 0014
Revises: 0013
Create Date: 2026-11-16 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0014"
down_revision: str | Sequence[str] | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("radar_runs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("error_code", sa.String(length=64), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("radar_runs", schema=None) as batch_op:
        batch_op.drop_column("error_code")
