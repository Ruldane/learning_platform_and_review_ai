from sqlalchemy import func, select

from app.db.models.research import WebQuery
from app.db.repository import UserScopedRepository


class WebQueryRepository(UserScopedRepository[WebQuery]):
    """Requêtes (nettoyées) lancées par les sessions d'un utilisateur."""

    model = WebQuery

    async def get(  # type: ignore[override]
        self, session_id: str, query_hash: str
    ) -> WebQuery | None:
        stmt = select(WebQuery).where(
            WebQuery.user_id == self.user_id,
            WebQuery.session_id == session_id,
            WebQuery.query_hash == query_hash,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def add(self, query: WebQuery) -> WebQuery:  # type: ignore[override]
        """Enregistre `query` pour cet utilisateur (le `user_id` reçu est ignoré)."""
        query.user_id = self.user_id
        self.session.add(query)
        await self.session.flush()
        return query

    async def count(self, session_id: str) -> int:
        stmt = (
            select(func.count())
            .select_from(WebQuery)
            .where(WebQuery.user_id == self.user_id, WebQuery.session_id == session_id)
        )
        return int((await self.session.execute(stmt)).scalar_one())
