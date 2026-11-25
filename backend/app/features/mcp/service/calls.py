"""The MCP call log (phase 10, P19) and the guarded dispatcher. Each tool call leaves a row:
the tool, its level, the result code, the duration and the ids touched, **never the content**
of the arguments or the response. `GuardedDispatcher` wraps B2's dispatcher: limits first
(429), log afterwards, even for a refused or failed call."""

import logging
import re
import time
from collections import deque
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.caller import McpIdentity
from app.core.errors import AppError
from app.db.models.mcp import McpCall
from app.features.mcp.repository import CallRepository
from app.features.mcp.schemas import McpCallOut
from app.mcp.limits import RateLimiter
from app.mcp.tools import Dispatcher, ToolResult, ToolSpec

logger = logging.getLogger(__name__)

_ID = re.compile(r"[A-Za-z0-9_-]{1,40}")
_MAX_IDS = 10
_REFUSALS_PER_MINUTE = 30
RETENTION_DAYS = 30  # the call log only keeps the last 30 days


def clean_ids(ids: Mapping[str, Any]) -> dict[str, Any]:
    """Bounds the ids and codes coming from the dispatcher before they are written to the log."""
    kept: dict[str, Any] = {}
    for key, value in list(ids.items())[:_MAX_IDS]:
        if not isinstance(key, str) or not _ID.fullmatch(key):
            continue
        if (
            isinstance(value, int)
            and not isinstance(value, bool)
            or isinstance(value, str)
            and _ID.fullmatch(value)
        ):
            kept[key] = value
    return kept


class CallJournal:
    """Writes a log row in its own short session (the call is already made)."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        fallback_user: Callable[[], str | None] = lambda: None,
    ) -> None:
        self._session_factory = session_factory
        self._fallback_user = fallback_user  # the local-mode user, for an unknown token
        self._refusals: dict[str, deque[float]] = {}

    async def record(
        self,
        identity: McpIdentity,
        tool: ToolSpec,
        code: int,
        duration_ms: int,
        ids: Mapping[str, Any],
        call_id: str | None = None,
    ) -> None:
        """A log failure does not cancel a call already made: reported, without content. A call
        refused by the limit (429) goes through the refusals budget: a client that insists does
        not write one row per request."""
        if code == 429 and not self._refusal_budget(f"{identity.token_id}|limit"):
            return
        try:
            async with self._session_factory() as db:
                await CallRepository(db, identity.user_id).record(
                    identity.token_id,
                    tool.name[:80],
                    tool.level,
                    code,
                    duration_ms,
                    clean_ids(ids),
                    call_id,
                )
                await db.commit()
        except Exception as exc:
            logger.error("MCP: logging the call is impossible (%s)", type(exc).__name__)

    def _refusal_budget(self, key: str) -> bool:
        """At most 30 rows per minute and per `key` (token and refusal reason: a flood of fake
        tokens fills neither the database nor hides a refusal of another reason)."""
        now = time.monotonic()
        recent = self._refusals.setdefault(key, deque())
        while recent and recent[0] <= now - 60:
            recent.popleft()
        if len(recent) >= _REFUSALS_PER_MINUTE:
            return False
        recent.append(now)
        return True

    async def refusal(
        self, user_id: str | None, token_id: str | None, action: str, level: int, code: int
    ) -> None:
        """Logs a refusal at the gate (level 0: before resolving the tool), never the content.
        Without a known account (unknown token), it is the local-mode user, or nothing."""
        owner = user_id or self._fallback_user()
        if owner is None or not self._refusal_budget(f"{token_id or '-'}|{action}"):
            return
        try:
            async with self._session_factory() as db:
                await CallRepository(db, owner).record(token_id, action[:80], level, code, 0, {})
                await db.commit()
        except Exception as exc:
            logger.error("MCP: logging the refusal is impossible (%s)", type(exc).__name__)


class GuardedDispatcher:
    """Limits then log around the real dispatcher."""

    def __init__(
        self,
        inner: Dispatcher,
        limiter: RateLimiter,
        journal: CallJournal,
    ) -> None:
        self._inner = inner
        self._limiter = limiter
        self._journal = journal

    async def call(
        self, identity: McpIdentity, tool: ToolSpec, arguments: dict[str, Any]
    ) -> ToolResult:
        started = time.monotonic()
        try:
            await self._limiter.check(identity, tool.level, datetime.now(UTC), bucket=tool.bucket)
            outcome = await self._inner.call(identity, tool, arguments)
        except AppError as exc:
            await self._journal.record(identity, tool, exc.status_code, _since(started), {})
            raise
        except Exception:
            await self._journal.record(identity, tool, 500, _since(started), {})
            raise
        await self._journal.record(
            identity, tool, outcome.code, _since(started), outcome.ids, outcome.call_id
        )
        return outcome


async def purge_old_calls(session_factory: async_sessionmaker[AsyncSession], now: datetime) -> int:
    """Removes from the log the calls older than `RETENTION_DAYS` days (scheduled task, all
    accounts: a retention, not a read). Returns the number of rows removed."""
    cutoff = now - timedelta(days=RETENTION_DAYS)
    async with session_factory() as db:
        result = await db.execute(delete(McpCall).where(McpCall.created_at < cutoff))
        await db.commit()
    return int(getattr(result, "rowcount", 0) or 0)


def _since(started: float) -> int:
    return round((time.monotonic() - started) * 1000)


class CallsService:
    """The log as January sees it: my calls, most recent first."""

    def __init__(self, db: AsyncSession, user_id: str) -> None:
        self._calls = CallRepository(db, user_id)

    async def recent(self, limit: int) -> list[McpCallOut]:
        return [McpCallOut.model_validate(row) for row in await self._calls.recent(limit)]
