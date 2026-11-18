"""Client MCP d'une session jouée et rendu réservé avant la reprise du graphe."""

import sqlalchemy as sa

from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sessions", sa.Column("played_by", sa.String(16), nullable=True))
    op.add_column("sessions", sa.Column("play_delivery", sa.JSON(), nullable=True))


def downgrade() -> None:
    # La suppression de la table pendant un batch effacerait ses événements en cascade.
    op.drop_column("sessions", "play_delivery")
    op.drop_column("sessions", "played_by")
