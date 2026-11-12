from datetime import datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.db.models.research import WebCacheEntry
from app.db.repository import UserScopedRepository


class WebCacheRepository(UserScopedRepository[WebCacheEntry]):
    """Cache web d'un utilisateur : jamais l'entrée d'un autre, jamais une entrée expirée."""

    model = WebCacheEntry

    async def get(  # type: ignore[override]
        self, kind: str, key_hash: str, now: datetime
    ) -> WebCacheEntry | None:
        stmt = (
            select(WebCacheEntry)
            .where(
                WebCacheEntry.user_id == self.user_id,
                WebCacheEntry.kind == kind,
                WebCacheEntry.key_hash == key_hash,
                WebCacheEntry.expires_at > now,
            )
            # Une entrée déjà chargée par cette session est relue : `put` la remplace en SQL.
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def put(
        self, kind: str, key_hash: str, status: str, payload: dict[str, Any], expires_at: datetime
    ) -> None:
        """Remplace l'entrée (ou la crée) en une seule instruction : deux écritures
        simultanées de la même clé ne lèvent pas d'erreur d'unicité."""
        values = {"status": status, "payload": payload, "expires_at": expires_at}
        stmt = sqlite_insert(WebCacheEntry).values(
            user_id=self.user_id, kind=kind, key_hash=key_hash, **values
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id", "kind", "key_hash"],
            set_={**values, "updated_at": stmt.excluded.updated_at},
        )
        await self.session.execute(stmt)

    async def purge_expired(self, now: datetime) -> int:
        stmt = delete(WebCacheEntry).where(
            WebCacheEntry.user_id == self.user_id, WebCacheEntry.expires_at <= now
        )
        result = await self.session.execute(stmt)
        return int(result.rowcount or 0)  # type: ignore[attr-defined]
