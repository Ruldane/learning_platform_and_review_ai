"""The agent log: a user's logged calls, newest first, by pages. The `before` cursor is
opaque: the instant and identifier of the page's last call, in unpadded base64 (`iso|id`)."""

import base64
import binascii
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Row
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.features.costs.repository import LlmCallRepository
from app.features.costs.schemas import AgentCallOut, AgentCallPage

_MAX_ID_LENGTH = 36  # `UserScopedMixin.id`: a UUID


def encode_cursor(at: datetime, call_id: str) -> str:
    """The cursor pointing at the call `call_id` made at instant `at` (rendered in UTC)."""
    raw = f"{at.astimezone(UTC).isoformat()}|{call_id}".encode()
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _bad_cursor() -> AppError:
    # Neither the received cursor nor the cause is echoed: `details.fields` names the field only.
    return AppError(
        "validation_error",
        "Invalid request: check the reported fields.",
        422,
        {"fields": ["before"]},
    )


def decode_cursor(raw: str) -> tuple[datetime, str]:
    """The instant (UTC, with time zone) and identifier of a cursor; 422 `before` if it is
    unreadable: invalid base64, text that is not UTF-8, date without time zone, empty or too
    long identifier."""
    try:
        padded = raw + "=" * (-len(raw) % 4)
        text = base64.b64decode(padded, altchars=b"-_", validate=True).decode("utf-8")
        stamp, separator, call_id = text.partition("|")
        at = datetime.fromisoformat(stamp)
        if not separator or at.tzinfo is None or not 0 < len(call_id) <= _MAX_ID_LENGTH:
            raise _bad_cursor()
        # A date that decodes but falls out of range once in UTC raises `OverflowError`.
        return at.astimezone(UTC), call_id
    except (binascii.Error, ValueError, OverflowError):  # `UnicodeDecodeError` : `ValueError`
        raise _bad_cursor() from None


def _out(row: Row[*tuple[Any, ...]]) -> AgentCallOut:
    return AgentCallOut(
        id=row.id,
        at=row.created_at,
        session_id=row.session_id,
        graph=row.graph,
        agent=row.agent,
        provider=row.provider,
        model=row.model,
        tokens_in=row.tokens_in,
        tokens_out=row.tokens_out,
        latency_ms=row.latency_ms,
        cost_usd=row.cost_usd,
        estimated=row.estimated,
    )


async def list_calls(
    db: AsyncSession,
    user_id: str,
    *,
    before: str | None,
    limit: int,
    agent: str | None,
    graph: str | None,
) -> AgentCallPage:
    """A page of at most `limit` calls; `next_before` exists only if more remain."""
    cursor = decode_cursor(before) if before is not None else None
    # One call more than requested: its mere presence says there is a next page.
    rows = await LlmCallRepository(db, user_id).page(
        before=cursor, limit=limit + 1, agent=agent, graph=graph
    )
    shown = rows[:limit]
    more = len(rows) > limit
    last = shown[-1] if shown else None
    return AgentCallPage(
        items=[_out(row) for row in shown],
        next_before=encode_cursor(last.created_at, last.id) if more and last else None,
    )
