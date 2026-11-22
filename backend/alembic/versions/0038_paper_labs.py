"""Conserver le mini-cours et la référence du notebook."""

import sqlalchemy as sa

from alembic import op

revision = "0038"
down_revision = "0037"


def upgrade() -> None:
    op.create_table(
        "paper_labs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("url", sa.String(2083), nullable=False),
        sa.Column("source_title", sa.String(240)),
        sa.Column("title", sa.String(180)),
        sa.Column("course", sa.Text()),
        sa.Column("expected", sa.Text()),
        sa.Column("ide_session_id", sa.String(36)),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("stage", sa.String(8), nullable=False),
    )
    op.create_index("ix_paper_labs_user_id", "paper_labs", ["user_id"])


def downgrade() -> None:
    op.drop_table("paper_labs")
