"""Étape et justification des semaines, pages officielles et API anciennes des modules."""

import sqlalchemy as sa

from alembic import op

revision = "0074"
down_revision = "0073"


def upgrade() -> None:
    with op.batch_alter_table("weeks") as batch_op:
        batch_op.add_column(sa.Column("stage", sa.String(16), nullable=True))
        batch_op.add_column(sa.Column("rationale", sa.Text(), nullable=True))
    with op.batch_alter_table("modules") as batch_op:
        batch_op.add_column(
            sa.Column("official_urls", sa.JSON(), nullable=False, server_default="[]")
        )
        batch_op.add_column(sa.Column("legacy", sa.JSON(), nullable=False, server_default="[]"))


def downgrade() -> None:
    # Pas de `batch_alter_table` : il recopie la table, et `DROP TABLE weeks` effacerait ses
    # modules et ses tâches en cascade. `DROP COLUMN` (SQLite 3.35) laisse les lignes en place.
    op.drop_column("modules", "legacy")
    op.drop_column("modules", "official_urls")
    op.drop_column("weeks", "rationale")
    op.drop_column("weeks", "stage")
