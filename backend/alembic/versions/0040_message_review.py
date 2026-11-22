"""Consentement à la révision Telegram et une réservation par jour local."""

from datetime import datetime

import sqlalchemy as sa

from alembic import op

revision = "0040"
down_revision = "0039"

_SETTINGS = "telegram_review_settings"
_CHALLENGES = "telegram_review_challenges"


def _scoped() -> tuple[sa.Column[str], sa.Column[str], sa.Column[datetime], sa.Column[datetime]]:
    return (
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def upgrade() -> None:
    op.create_table(
        _SETTINGS,
        *_scoped(),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("start", sa.String(5), nullable=False),
        sa.Column("end", sa.String(5), nullable=False),
        sa.Column("token_id", sa.String(36), nullable=True),
        sa.Column("chat_id", sa.String(19), nullable=True),
        sa.Column("consent_id", sa.String(36), nullable=False),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(f"ix_{_SETTINGS}_user_id", _SETTINGS, ["user_id"])
    op.create_table(
        _CHALLENGES,
        *_scoped(),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("consent_id", sa.String(36), nullable=False),
        sa.Column(
            "card_id",
            sa.String(36),
            sa.ForeignKey("flashcards.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rating", sa.String(4), nullable=True),
        sa.Column("outcome", sa.JSON(), nullable=True),
        sa.UniqueConstraint("user_id", "day"),
    )
    op.create_index(f"ix_{_CHALLENGES}_user_id", _CHALLENGES, ["user_id"])


def downgrade() -> None:
    op.drop_table(_CHALLENGES)
    op.drop_table(_SETTINGS)
