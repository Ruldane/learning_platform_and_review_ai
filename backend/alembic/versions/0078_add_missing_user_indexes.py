"""Add the user indexes declared by LinkedIn drafts and offline review receipts."""

from alembic import op

revision = "0078"
down_revision = "0077"

_TABLES = ("linkedin_drafts", "offline_reviews")


def upgrade() -> None:
    for table in _TABLES:
        op.create_index(f"ix_{table}_user_id", table, ["user_id"])


def downgrade() -> None:
    for table in _TABLES:
        op.drop_index(f"ix_{table}_user_id", table_name=table)
