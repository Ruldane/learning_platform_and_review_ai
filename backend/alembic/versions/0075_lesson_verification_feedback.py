"""Remarques détaillées du dernier contrôle refusé d'une leçon soumise (D308)."""

import sqlalchemy as sa

from alembic import op

revision = "0075"
down_revision = "0074"


def upgrade() -> None:
    with op.batch_alter_table("lessons") as batch_op:
        batch_op.add_column(sa.Column("verification_feedback", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("lessons") as batch_op:
        batch_op.drop_column("verification_feedback")
