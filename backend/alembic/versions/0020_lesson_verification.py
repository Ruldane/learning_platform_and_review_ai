"""Brouillon privé et session de vérification des écritures de leçon."""

import sqlalchemy as sa

from alembic import op

revision = "0020"
down_revision = "0019"


def upgrade() -> None:
    op.add_column("lessons", sa.Column("verification_session_id", sa.String(36)))
    op.add_column("lessons", sa.Column("verification_failure_reason", sa.String(300)))
    op.add_column("lessons", sa.Column("verification_draft", sa.JSON()))


def downgrade() -> None:
    op.drop_column("lessons", "verification_draft")
    op.drop_column("lessons", "verification_failure_reason")
    op.drop_column("lessons", "verification_session_id")
