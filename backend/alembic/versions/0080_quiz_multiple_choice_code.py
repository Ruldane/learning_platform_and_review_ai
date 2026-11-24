"""Use the English code for multiple-choice questions."""

from alembic import op

revision = "0080"
down_revision = "0079"


def upgrade() -> None:
    op.execute("UPDATE quiz_questions SET type = 'mcq' WHERE type = 'qcm'")


def downgrade() -> None:
    op.execute("UPDATE quiz_questions SET type = 'qcm' WHERE type = 'mcq'")
