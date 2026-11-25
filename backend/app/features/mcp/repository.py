"""Access to the MCP tables (phase 10): tokens, master switch, call journal. Everything is
filtered by `user_id`. Looking up a token by its fingerprint (without `user_id`, we do not
know yet whose it is) lives only in `app.mcp.auth`."""

from datetime import datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.mcp import McpCall, McpChange, McpConfirmation, McpPrefs, McpToken
from app.db.repository import UserScopedRepository


class TokenRepository(UserScopedRepository[McpToken]):
    model = McpToken

    async def newest_first(self) -> list[McpToken]:
        stmt = (
            select(McpToken)
            .where(McpToken.user_id == self.user_id)
            .order_by(McpToken.created_at.desc(), McpToken.id)
        )
        return list((await self.session.execute(stmt)).scalars())

    async def revoke(self, token_id: str, now: datetime) -> McpToken | None:
        """Sets `revoked_at` (never deleted: the journal keeps its `token_id`); an already revoked
        token keeps its date."""
        row = await self.get(token_id)
        if row is not None and row.revoked_at is None:
            row.revoked_at = now
            await self.session.flush()
        return row


class PrefsRepository:
    """The master switch, one row per account (absent = off)."""

    def __init__(self, session: AsyncSession, user_id: str) -> None:
        self.session = session
        self.user_id = user_id

    async def get(self) -> McpPrefs | None:
        stmt = select(McpPrefs).where(McpPrefs.user_id == self.user_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def set_enabled(self, enabled: bool) -> McpPrefs:
        row = await self.get()
        if row is None:
            row = McpPrefs(user_id=self.user_id, enabled=enabled)
            self.session.add(row)
        else:
            row.enabled = enabled
        await self.session.flush()
        return row


class CallRepository(UserScopedRepository[McpCall]):
    model = McpCall

    async def record(
        self,
        token_id: str | None,
        action: str,
        level: int,
        code: int,
        duration_ms: int,
        ids: dict[str, Any],
        call_id: str | None = None,
    ) -> McpCall:
        """`call_id`: the identifier set on the row (the one of the call's changes)."""
        extra: dict[str, Any] = {} if call_id is None else {"id": call_id}
        return await self.add(
            **extra,
            token_id=token_id,
            action=action,
            level=level,
            code=code,
            duration_ms=duration_ms,
            ids=ids,
        )

    async def recent(self, limit: int) -> list[McpCall]:
        stmt = (
            select(McpCall)
            .where(McpCall.user_id == self.user_id)
            .order_by(McpCall.created_at.desc(), McpCall.id)
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars())


class ConfirmationRepository(UserScopedRepository[McpConfirmation]):
    """Pending confirmations. Each state change is a conditional `UPDATE` (expected state in the
    `WHERE`): two simultaneous clicks never both go through."""

    model = McpConfirmation

    async def pending_count(self, token_id: str, now: datetime) -> int:
        stmt = select(func.count()).where(
            McpConfirmation.user_id == self.user_id,
            McpConfirmation.token_id == token_id,
            McpConfirmation.status == "pending",
            McpConfirmation.expires_at > now,
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def recent(self, limit: int) -> list[McpConfirmation]:
        stmt = (
            select(McpConfirmation)
            .where(McpConfirmation.user_id == self.user_id)
            .order_by(McpConfirmation.created_at.desc(), McpConfirmation.id)
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars())

    async def transition(
        self,
        confirmation_id: str,
        source: str,
        target: str,
        now: datetime,
        *,
        live_only: bool = False,
        result_code: int | None = None,
    ) -> bool:
        """Moves the request from `source` to `target` if it is still there; `live_only`: only if it
        has not expired. True if this request made the move."""
        conditions = [
            McpConfirmation.id == confirmation_id,
            McpConfirmation.user_id == self.user_id,
            McpConfirmation.status == source,
        ]
        if live_only:
            conditions.append(McpConfirmation.expires_at > now)
        values: dict[str, Any] = {"status": target, "decided_at": now}
        if result_code is not None:
            values["result_code"] = result_code
        result = await self.session.execute(
            update(McpConfirmation).where(*conditions).values(**values)
        )
        return int(getattr(result, "rowcount", 0) or 0) == 1

    async def set_precheck(self, confirmation_id: str, precheck: dict[str, Any] | None) -> None:
        """Replaces the verdict of a request still pending (check replayed on click)."""
        await self.session.execute(
            update(McpConfirmation)
            .where(
                McpConfirmation.id == confirmation_id,
                McpConfirmation.user_id == self.user_id,
                McpConfirmation.status == "pending",
            )
            .values(precheck=precheck)
        )


async def expire_pending(session: AsyncSession, now: datetime) -> int:
    """Any pending request whose time has passed becomes "expired" (scheduled task, all accounts: a
    maintenance job, not a data read)."""
    stmt = (
        update(McpConfirmation)
        .where(McpConfirmation.status == "pending", McpConfirmation.expires_at <= now)
        .values(status="expired", decided_at=now)
    )
    return int(getattr(await session.execute(stmt), "rowcount", 0) or 0)


class ChangeRepository(UserScopedRepository[McpChange]):
    """The changes kept per call (history of level 2 writes)."""

    model = McpChange

    async def calls(self, limit: int) -> list[tuple[str, int, datetime, datetime | None]]:
        """One tuple per call: `(call_id, rows, date, undone_at)`, most recent first."""
        stmt = (
            select(
                McpChange.call_id,
                func.count(),
                func.max(McpChange.created_at),
                func.min(McpChange.undone_at),
                func.count(McpChange.undone_at),
            )
            .where(McpChange.user_id == self.user_id)
            .group_by(McpChange.call_id)
            .order_by(func.max(McpChange.created_at).desc())
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).all()
        # `annulé le` only if all the rows are.
        return [(r[0], r[1], r[2], r[3] if r[4] == r[1] else None) for r in rows]

    async def tables(self, call_ids: list[str]) -> dict[str, list[str]]:
        stmt = (
            select(McpChange.call_id, McpChange.table_name)
            .where(McpChange.user_id == self.user_id, McpChange.call_id.in_(call_ids))
            .distinct()
        )
        found: dict[str, list[str]] = {}
        for call_id, table in (await self.session.execute(stmt)).all():
            found.setdefault(call_id, []).append(table)
        return {key: sorted(value) for key, value in found.items()}

    async def actions(self, call_ids: list[str]) -> dict[str, str]:
        """The tool of each call (the journal row carries the call's identifier)."""
        stmt = select(McpCall.id, McpCall.action).where(
            McpCall.user_id == self.user_id, McpCall.id.in_(call_ids)
        )
        return {call_id: action for call_id, action in (await self.session.execute(stmt)).all()}
