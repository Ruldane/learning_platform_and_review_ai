"""Conserver une réponse acceptée jusqu'à son prochain checkpoint."""

import sqlalchemy as sa

from alembic import op

revision = "0058a"
down_revision = "0058"


def upgrade() -> None:
    op.add_column("sessions", sa.Column("user_delivery", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("sessions", "user_delivery")
