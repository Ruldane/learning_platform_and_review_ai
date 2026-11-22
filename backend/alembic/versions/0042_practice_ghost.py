"""Repères de version et temps de jeu des nouveaux défis personnels."""

import sqlalchemy as sa

from alembic import op

revision = "0042"
down_revision = "0041"


def upgrade() -> None:
    op.add_column("quiz_attempts", sa.Column("question_version", sa.String(64)))
    op.add_column("quiz_attempts", sa.Column("elapsed_ms", sa.Integer()))
    op.add_column("ide_sessions", sa.Column("exercise_version", sa.String(64)))
    op.add_column("ide_sessions", sa.Column("exercise_statement", sa.Text()))


def downgrade() -> None:
    op.drop_column("ide_sessions", "exercise_statement")
    op.drop_column("ide_sessions", "exercise_version")
    op.drop_column("quiz_attempts", "elapsed_ms")
    op.drop_column("quiz_attempts", "question_version")
