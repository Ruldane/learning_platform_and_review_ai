"""documents.tags : étiquettes d'un document rangé par une feature (profil maître, D124)

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-14 08:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0009"
down_revision: str | Sequence[str] | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("documents", schema=None) as batch_op:
        batch_op.add_column(sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("documents", schema=None) as batch_op:
        batch_op.drop_column("tags")
