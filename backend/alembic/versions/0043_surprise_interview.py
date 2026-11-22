"""Consentement et invitations d’entretien surprise."""

import sqlalchemy as sa

from alembic import op

revision = "0043"
down_revision = "0042"

_SETTINGS = "surprise_interview_settings"
_INVITATIONS = "surprise_interview_invitations"
_FK = "fk_interviews_surprise_invitation_id_surprise_interview_invitations"


def _scoped() -> tuple[sa.Column, ...]:
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
        sa.Column("token_id", sa.String(36)),
        sa.Column("chat_consent_id", sa.String(36)),
        sa.Column("consent_id", sa.String(36), nullable=False),
        sa.Column("role", sa.String(200), nullable=False),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(f"ix_{_SETTINGS}_user_id", _SETTINGS, ["user_id"])
    op.create_table(
        _INVITATIONS,
        *_scoped(),
        sa.Column("week", sa.Date(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("consent_id", sa.String(36), nullable=False),
        sa.Column("role", sa.String(200), nullable=False),
        sa.Column("answers", sa.JSON(), nullable=False),
        sa.UniqueConstraint("user_id", "week"),
    )
    op.create_index(f"ix_{_INVITATIONS}_user_id", _INVITATIONS, ["user_id"])
    with op.batch_alter_table("interviews") as batch:
        batch.add_column(sa.Column("surprise_invitation_id", sa.String(36)))
        batch.create_foreign_key(
            _FK, _INVITATIONS, ["surprise_invitation_id"], ["id"], ondelete="RESTRICT"
        )


def downgrade() -> None:
    with op.batch_alter_table("interviews") as batch:
        batch.drop_constraint(_FK, type_="foreignkey")
        batch.drop_column("surprise_invitation_id")
    op.drop_table(_INVITATIONS)
    op.drop_table(_SETTINGS)
