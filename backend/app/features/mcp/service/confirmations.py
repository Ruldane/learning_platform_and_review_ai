"""The "To confirm" requests (phase 10, P15): a level 3 tool never runs by itself, it leaves a
request here. January confirms it (the request runs **only once**, under the recorded
identity), refuses it, or it expires after 24 h. Each state transition is a conditional
`UPDATE`: two clicks at the same time, or a click on an expired or refused request, never make
the request run twice nor afterwards."""

import logging
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any, NamedTuple, NoReturn

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.caller import McpIdentity
from app.core.errors import AppError
from app.features.mcp.repository import (
    CallRepository,
    ConfirmationRepository,
    PrefsRepository,
    TokenRepository,
    expire_pending,
)
from app.features.mcp.schemas import McpConfirmationOut
from app.features.mcp.service.calls import clean_ids
from app.features.mcp.service.confirmation_support import confirmation_out, verdict_key
from app.mcp.confirm import (
    CONFIRMATION_TTL,
    MAX_PENDING_PER_TOKEN,
    StoredRequest,
)
from app.mcp.tools import ToolResult

logger = logging.getLogger(__name__)

Executor = Callable[[McpIdentity, StoredRequest], Awaitable[ToolResult]]
# Replays the tool's prior check (`None`: the tool has none).
Rechecker = Callable[[McpIdentity, StoredRequest], Awaitable[dict[str, Any] | None]]
LIST_LIMIT = 100


async def expire_due(session_factory: async_sessionmaker[AsyncSession], now: datetime) -> int:
    """Pending requests whose time has passed become "expired" (scheduled task).
    Returns their number."""
    async with session_factory() as db:
        count = await expire_pending(db, now)
        await db.commit()
    return count


_REVOKED = "The token used for this request was revoked. The request was refused."
_EXPIRED = "The token used for this request expired. The request was refused."


def _closed(status: str) -> AppError:
    messages = {
        "confirmed": "This request is already confirmed.",
        "refused": "This request was refused.",
        "expired": "This request has expired.",
    }
    message = messages.get(status, "This request has already been handled.")
    return AppError("confirmation_closed", message, 409)


def _not_found() -> AppError:
    return AppError("confirmation_not_found", "Request not found.", 404)


class _Claimed(NamedTuple):
    stored: StoredRequest
    token_id: str
    action: str
    precheck: dict[str, Any] | None


class ConfirmationService:
    """An account's requests. `execute`: the sender that replays the recorded request (absent
    for creation, list and refusal)."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        user_id: str,
        execute: Executor | None = None,
        recheck: Rechecker | None = None,
    ) -> None:
        self._factory = session_factory
        self._user_id = user_id
        self._execute = execute
        self._recheck = recheck

    def _repo(self, db: AsyncSession) -> ConfirmationRepository:
        return ConfirmationRepository(db, self._user_id)

    async def create(
        self,
        identity: McpIdentity,
        stored: StoredRequest,
        summary: str,
        precheck: dict[str, Any] | None,
    ) -> McpConfirmationOut:
        """Stores the request (24 h); 429 `too_many_pending` at 20 pending requests for this
        token."""
        now = datetime.now(UTC)
        async with self._factory() as db:
            repo = self._repo(db)
            await self._room(repo, identity, now)
            row = await repo.add(
                token_id=identity.token_id,
                action=stored.tool[:80],
                request=stored.to_json(),
                summary=summary,
                precheck=precheck,
                status="pending",
                expires_at=now + CONFIRMATION_TTL,
            )
            created = confirmation_out(row)
            await db.commit()
        return created

    @staticmethod
    async def _room(repo: ConfirmationRepository, identity: McpIdentity, now: datetime) -> None:
        if await repo.pending_count(identity.token_id, now) >= MAX_PENDING_PER_TOKEN:
            raise AppError(
                "too_many_pending",
                f"This token has {MAX_PENDING_PER_TOKEN} pending requests. "
                "Confirm or refuse one before adding more.",
                429,
                {"limit": MAX_PENDING_PER_TOKEN},
            )

    async def ensure_room(self, identity: McpIdentity) -> None:
        """429 `too_many_pending` if the token already has 20 pending requests (before the prior
        check, which may cost a model call)."""
        async with self._factory() as db:
            await self._room(self._repo(db), identity, datetime.now(UTC))

    async def list(self) -> list[McpConfirmationOut]:
        """My requests, most recent first (stale ones are marked first)."""
        async with self._factory() as db:
            await expire_pending(db, datetime.now(UTC))
            rows = await self._repo(db).recent(LIST_LIMIT)
            listed = [confirmation_out(row) for row in rows]
            await db.commit()
        return listed

    async def get(self, confirmation_id: str) -> McpConfirmationOut:
        async with self._factory() as db:
            row = await self._repo(db).get(confirmation_id)
            if row is None:
                raise _not_found()
            return confirmation_out(row)

    async def expire_due(self) -> int:
        return await expire_due(self._factory, datetime.now(UTC))

    async def refuse(self, confirmation_id: str) -> McpConfirmationOut:
        """Refuses: it will never run. 409 if it is already decided or expired."""
        now = datetime.now(UTC)
        async with self._factory() as db:
            repo = self._repo(db)
            row = await repo.get(confirmation_id)
            if row is None:
                raise _not_found()
            status = row.status
            if not await repo.transition(
                confirmation_id, "pending", "refused", now, live_only=True
            ):
                await repo.transition(confirmation_id, "pending", "expired", now)
                await db.commit()
                raise _closed("expired" if status == "pending" else status)
            await db.commit()
        return await self.get(confirmation_id)

    async def confirm(self, confirmation_id: str) -> ToolResult:
        """Executes the request, once only, under the recorded identity. 404 unknown; 409
        expired (it will never run), refused, already handled, token revoked or expired, master
        switch off, or prior check that has become different since the request."""
        if self._execute is None:
            raise RuntimeError("confirmation without a sender")
        now = datetime.now(UTC)
        async with self._factory() as db:
            claimed = await self._load(db, confirmation_id, now)
        identity = claimed.stored.identity(self._user_id, claimed.token_id)
        await self._recheck_verdict(confirmation_id, identity, claimed)
        async with self._factory() as db:
            await self._take(db, confirmation_id, now)
        started = time.monotonic()
        try:
            result = await self._execute(identity, claimed.stored)
        except Exception as exc:  # the request is taken: it does not restart, it fails
            logger.error("MCP: executing a request is impossible (%s)", type(exc).__name__)
            error = {"error": {"code": "execution_failed", "message": "The request failed to run."}}
            result = ToolResult(data=error, code=500)
        elapsed = round((time.monotonic() - started) * 1000)
        async with self._factory() as db:
            status = "failed" if result.is_error else "confirmed"
            retained = await self._repo(db).transition(
                confirmation_id, "confirmed", status, now, result_code=result.code
            )
            if retained:
                await CallRepository(db, self._user_id).record(
                    claimed.token_id,
                    f"{claimed.action}:confirm"[:80],
                    3,
                    result.code,
                    elapsed,
                    clean_ids(result.ids),
                )
            await db.commit()
        return result

    async def _load(self, db: AsyncSession, confirmation_id: str, now: datetime) -> _Claimed:
        """Re-reads the request and what it depends on: still pending, token valid (neither
        revoked nor expired: otherwise it is refused), master switch on (otherwise it waits)."""
        repo = self._repo(db)
        row = await repo.get(confirmation_id)
        if row is None:
            raise _not_found()
        if row.status == "pending" and row.expires_at <= now:
            await repo.transition(confirmation_id, "pending", "expired", now)
            await db.commit()
            raise _closed("expired")
        if row.status != "pending":
            raise _closed(row.status)
        token = await TokenRepository(db, self._user_id).get(row.token_id)
        if token is None or token.revoked_at is not None:
            await self._refuse_for(db, confirmation_id, now, "token_revoked", _REVOKED)
        elif token.expires_at <= now:
            await self._refuse_for(db, confirmation_id, now, "token_expired", _EXPIRED)
        prefs = await PrefsRepository(db, self._user_id).get()
        if prefs is None or not prefs.enabled:
            raise AppError(
                "mcp_disabled",
                "Enable MCP access in settings, then confirm the request again.",
                409,
            )
        stored = StoredRequest.from_json(row.request)
        return _Claimed(stored, row.token_id, row.action, row.precheck)

    async def _refuse_for(
        self, db: AsyncSession, confirmation_id: str, now: datetime, code: str, message: str
    ) -> NoReturn:
        await self._repo(db).transition(confirmation_id, "pending", "refused", now)
        await db.commit()
        raise AppError(code, message, 409)

    async def _recheck_verdict(
        self, confirmation_id: str, identity: McpIdentity, claimed: _Claimed
    ) -> None:
        """Replays the prior check: the request's verdict may date from a day ago. If it has
        changed, the request keeps the new verdict and waits (readable refusal, nothing runs):
        January re-reads it, then confirms again."""
        if self._recheck is None:
            return
        fresh = await self._recheck(identity, claimed.stored)
        if verdict_key(fresh) == verdict_key(claimed.precheck):
            return
        async with self._factory() as db:
            await self._repo(db).set_precheck(confirmation_id, fresh)
            await db.commit()
        raise AppError(
            "precheck_changed",
            "The precheck result has changed. Review the new result and confirm again.",
            409,
        )

    async def _take(self, db: AsyncSession, confirmation_id: str, now: datetime) -> None:
        """Takes the request (atomic transition "pending" -> "confirmed"), or refuses."""
        if not await self._repo(db).transition(
            confirmation_id, "pending", "confirmed", now, live_only=True
        ):
            await db.commit()
            raise _closed("confirmed")
        await db.commit()
