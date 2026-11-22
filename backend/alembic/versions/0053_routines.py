"""Routines quotidiennes et reçus d'exécution."""

import sqlalchemy as sa

from alembic import op

revision = "0053"
down_revision = "0052"


def _owned_columns() -> list[sa.Column[object]]:
    return [
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "routines",
        *_owned_columns(),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("local_time", sa.String(5), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.UniqueConstraint("user_id", "action"),
    )
    op.create_index("ix_routines_user_id", "routines", ["user_id"])
    op.create_table(
        "routine_executions",
        *_owned_columns(),
        sa.Column(
            "routine_id",
            sa.String(36),
            sa.ForeignKey("routines.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("occurrence", sa.String(48), nullable=False),
        sa.Column("source", sa.String(12), nullable=False),
        sa.Column("result_count", sa.Integer(), nullable=False),
        sa.Column("notices", sa.JSON(), nullable=False),
        sa.UniqueConstraint("user_id", "routine_id", "occurrence"),
    )
    op.create_index("ix_routine_executions_user_id", "routine_executions", ["user_id"])


def downgrade() -> None:
    op.drop_table("routine_executions")
    op.drop_table("routines")
