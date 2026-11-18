"""Fournisseur d'API forcé pour tout un parcours (« API GLM », « API Claude », « API OpenAI »)."""

import sqlalchemy as sa

from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sessions", sa.Column("model_provider", sa.String(16), nullable=True))


def downgrade() -> None:
    op.drop_column("sessions", "model_provider")
