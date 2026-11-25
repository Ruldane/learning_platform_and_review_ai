from datetime import datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.db.models.research import WebCacheEntry
from app.db.repository import UserScopedRepository


class WebCacheRepository(UserScopedRepository[WebCacheEntry]):
    """A user's web cache: never another user's entry, never an expired entry."""

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
            # An entry already loaded by this session is re-read: `put` replaces it in SQL.
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def put(
        self, kind: str, key_hash: str, status: str, payload: dict[str, Any], expires_at: datetime
    ) -> None:
        """Replaces the entry (or creates it) in a single statement: two simultaneous writes of the
        same key do not raise a uniqueness error."""
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
