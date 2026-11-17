"""L'interrupteur général du MCP (phase 10, P16) : coupé par défaut, un geste le coupe ou le
rallume pour tous les jetons à la fois (la porte le relit à chaque appel)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.mcp.repository import PrefsRepository
from app.features.mcp.schemas import McpSettingsOut


class PrefsService:
    def __init__(self, db: AsyncSession, user_id: str) -> None:
        self._prefs = PrefsRepository(db, user_id)

    async def get(self) -> McpSettingsOut:
        row = await self._prefs.get()
        return McpSettingsOut(enabled=bool(row and row.enabled))

    async def set_enabled(self, enabled: bool) -> McpSettingsOut:
        row = await self._prefs.set_enabled(enabled)
        return McpSettingsOut(enabled=row.enabled)
