"""Module de validation des acquis : quiz écrit d'après les compétences, sans leçon."""

import sqlalchemy as sa

from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("modules", sa.Column("kind", sa.String(16), nullable=True))


def downgrade() -> None:
    op.drop_column("modules", "kind")
