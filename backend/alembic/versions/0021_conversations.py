"""Fils et tours du moteur de conversation."""

import sqlalchemy as sa

from alembic import op

revision = "0021"
down_revision = "0020"


def _common() -> tuple[sa.Column, ...]:
    return (
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def upgrade() -> None:
    op.create_table(
        "conversations",
        *_common(),
        sa.Column("scope", sa.String(24), nullable=False),
        sa.Column("subject_id", sa.String(36), nullable=False),
        sa.UniqueConstraint("user_id", "scope", "subject_id", name="uq_conversations_scope"),
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])
    op.create_table(
        "conversation_turns",
        *_common(),
        sa.Column(
            "thread_id",
            sa.String(36),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("request_id", sa.String(36), nullable=False),
        sa.Column(
            "session_id",
            sa.String(36),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("passage", sa.Text),
        sa.Column("passage_occurrence", sa.Integer),
        sa.Column("lesson_version", sa.String(64)),
        sa.Column("mcp_call_id", sa.String(36)),
        sa.Column("strong", sa.Boolean, nullable=False),
        sa.Column("answer", sa.Text),
        sa.Column("sources", sa.JSON, nullable=False),
        sa.UniqueConstraint("thread_id", "request_id", name="uq_conversation_turns_request"),
    )
    op.create_index("ix_conversation_turns_user_id", "conversation_turns", ["user_id"])


def downgrade() -> None:
    op.drop_table("conversation_turns")
    op.drop_table("conversations")
