"""MCP server tables (phase 10, P3, P14 to P19): tokens, master switch, call journal, change
history (undo) and « À confirmer » requests. No foreign key: the journal and the history
outlive the revocation of a token."""

from datetime import datetime
from typing import Any, Literal

from sqlalchemy import Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UserScopedMixin, UTCDateTime

McpMode = Literal["read", "write"]
ConfirmationStatus = Literal["pending", "confirmed", "refused", "expired", "failed"]
ChangeOp = Literal["insert", "update", "delete"]


class McpToken(UserScopedMixin, Base):
    """An MCP access token (P16): `tmcp_` + 32 random bytes; **only the SHA-256 is kept** (`hash`,
    never exported, never logged), and the value is shown only once.
    `features`: the open features; `mode`: `read` by default; `expires_at`: 1, 7, 30 or 90
    days after creation."""

    __tablename__ = "mcp_tokens"
    # `uq_mcp_tokens_hash`: one fingerprint identifies a single token.
    __table_args__ = (UniqueConstraint("hash"),)

    label: Mapped[str] = mapped_column(String(60))
    hash: Mapped[str] = mapped_column(String(64), info={"export": False})
    features: Mapped[list[Any]] = mapped_column(default=list)
    mode: Mapped[str] = mapped_column(String(8), default="read")
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)
    last_used_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)


class McpPrefs(UserScopedMixin, Base):
    """The MCP master switch, one row per account. Off by default (P16): without a row, or with
    `enabled` false, no token opens anything."""

    __tablename__ = "mcp_prefs"
    # `uq_mcp_prefs_user_id`: one row per account.
    __table_args__ = (UniqueConstraint("user_id"),)

    enabled: Mapped[bool] = mapped_column(default=False)


class McpRelayPairing(UserScopedMixin, Base):
    """The temporary code and the last token dedicated to this account's relay."""

    __tablename__ = "mcp_relay_pairings"
    __table_args__ = (UniqueConstraint("user_id"), UniqueConstraint("code_hash"))

    code_hash: Mapped[str | None] = mapped_column(String(64), info={"export": False})
    code_expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    token_id: Mapped[str | None] = mapped_column(String(36))


class McpCall(UserScopedMixin, Base):
    """A tool call (P19): the tool, its level, the result code (HTTP), the duration and the
    identifiers touched. **Never the content** of the parameters or of the response. A refused
    call is logged too: `level` 0 = refused before the tool was resolved; `token_id` empty =
    unrecognized token."""

    __tablename__ = "mcp_calls"
    __table_args__ = (Index("ix_mcp_calls_user_created", "user_id", "created_at"),)

    token_id: Mapped[str | None] = mapped_column(String(36), index=True, default=None)
    action: Mapped[str] = mapped_column(String(80))
    level: Mapped[int] = mapped_column(Integer)
    code: Mapped[int] = mapped_column(Integer)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    ids: Mapped[dict[str, Any]] = mapped_column(default=dict)


class McpChange(UserScopedMixin, Base):
    """A row touched by a level 2 call (P14): the state before and after (`before`, `after`; empty
    for an addition or a deletion). `undo(call_id)` applies the inverse **if the row is still
    in the "after" state**. `undone_at`: set once undone."""

    __tablename__ = "mcp_changes"
    __table_args__ = (Index("ix_mcp_changes_call", "call_id"),)

    call_id: Mapped[str] = mapped_column(String(36))
    table_name: Mapped[str] = mapped_column(String(64))
    row_id: Mapped[str] = mapped_column(String(36))
    op: Mapped[str] = mapped_column(String(8))
    before: Mapped[dict[str, Any] | None] = mapped_column(default=None)
    after: Mapped[dict[str, Any] | None] = mapped_column(default=None)
    undone_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)


class McpConfirmation(UserScopedMixin, Base):
    """A « À confirmer » request (P15): the full request (method, path, parameters, body), a neutral
    summary and the verdict of any prior check. Expires after 24 h; on confirmation, the request
    runs only once under the recorded identity."""

    __tablename__ = "mcp_confirmations"
    __table_args__ = (Index("ix_mcp_confirmations_user_status", "user_id", "status"),)

    token_id: Mapped[str] = mapped_column(String(36), index=True)
    action: Mapped[str] = mapped_column(String(80))
    request: Mapped[dict[str, Any]] = mapped_column(default=dict)
    summary: Mapped[str] = mapped_column(Text, default="")
    precheck: Mapped[dict[str, Any] | None] = mapped_column(default=None)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    decided_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)
    result_code: Mapped[int | None] = mapped_column(Integer, default=None)
