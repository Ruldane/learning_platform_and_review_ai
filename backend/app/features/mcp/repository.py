"""Accès aux tables du MCP (phase 10) : jetons, interrupteur général, journal des appels. Tout est
filtré par `user_id`. La recherche d'un jeton par son empreinte (sans `user_id`, on ne sait pas
encore à qui il est) vit dans `app.mcp.auth`, seule."""

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.mcp import McpCall, McpPrefs, McpToken
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
        """Pose `revoked_at` (jamais d'effacement : le journal garde son `token_id`) ; un jeton
        déjà révoqué garde sa date."""
        row = await self.get(token_id)
        if row is not None and row.revoked_at is None:
            row.revoked_at = now
            await self.session.flush()
        return row


class PrefsRepository:
    """L'interrupteur général, une ligne par compte (absente = coupé)."""

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
    ) -> McpCall:
        return await self.add(
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
