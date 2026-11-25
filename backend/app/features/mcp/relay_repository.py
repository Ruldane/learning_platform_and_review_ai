"""Access to the relay code and atomic consumption within the token transaction."""

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.mcp import McpRelayPairing


class RelayRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._db = session

    async def get(self, user_id: str) -> McpRelayPairing | None:
        stmt = select(McpRelayPairing).where(McpRelayPairing.user_id == user_id)
        return (await self._db.execute(stmt)).scalar_one_or_none()

    async def issue(self, user_id: str, digest: str, expires_at: datetime, now: datetime) -> None:
        stmt = insert(McpRelayPairing).values(
            user_id=user_id, code_hash=digest, code_expires_at=expires_at
        )
        await self._db.execute(
            stmt.on_conflict_do_update(
                index_elements=[McpRelayPairing.user_id],
                set_={"code_hash": digest, "code_expires_at": expires_at, "updated_at": now},
            )
        )

    async def claim(self, digest: str, now: datetime) -> tuple[str, str | None] | None:
        # The account is unknown until the code is consumed, as for an MCP token.
        stmt = (
            update(McpRelayPairing)
            .where(McpRelayPairing.code_hash == digest, McpRelayPairing.code_expires_at > now)
            .values(code_hash=None, code_expires_at=None)
            .returning(McpRelayPairing.user_id, McpRelayPairing.token_id)
        )
        row = (await self._db.execute(stmt)).one_or_none()
        return (row.user_id, row.token_id) if row is not None else None

    async def attach(self, user_id: str, token_id: str) -> None:
        await self._db.execute(
            update(McpRelayPairing)
            .where(McpRelayPairing.user_id == user_id)
            .values(token_id=token_id)
        )

    async def cancel(self, user_id: str, now: datetime) -> str | None:
        stmt = (
            update(McpRelayPairing)
            .where(McpRelayPairing.user_id == user_id)
            .values(code_hash=None, code_expires_at=None, updated_at=now)
            .returning(McpRelayPairing.token_id)
        )
        return (await self._db.execute(stmt)).scalar_one_or_none()
