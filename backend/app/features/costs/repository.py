from datetime import datetime

from sqlalchemy import and_, or_, select

from app.db.models.agents import LlmCall
from app.db.repository import UserScopedRepository


class LlmCallRepository(UserScopedRepository[LlmCall]):
    """Lecture du journal des appels (`llm_calls`), au nom d'une seule utilisatrice."""

    model = LlmCall

    async def since(self, start_utc: datetime) -> list[LlmCall]:
        """Les appels faits à partir de `start_utc` (inclus), du plus ancien au plus récent."""
        stmt = (
            select(LlmCall)
            .where(LlmCall.user_id == self.user_id, LlmCall.created_at >= start_utc)
            .order_by(LlmCall.created_at, LlmCall.id)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def page(
        self,
        *,
        before: tuple[datetime, str] | None,
        limit: int,
        agent: str | None,
        graph: str | None,
    ) -> list[LlmCall]:
        """`limit` appels du plus récent au plus ancien, strictement avant le curseur
        `(created_at, id)` s'il y en a un ; `agent` et `graph` filtrent."""
        stmt = select(LlmCall).where(LlmCall.user_id == self.user_id)
        if before is not None:
            at, call_id = before
            stmt = stmt.where(
                or_(
                    LlmCall.created_at < at,
                    and_(LlmCall.created_at == at, LlmCall.id < call_id),
                )
            )
        if agent is not None:
            stmt = stmt.where(LlmCall.agent == agent)
        if graph is not None:
            stmt = stmt.where(LlmCall.graph == graph)
        stmt = stmt.order_by(LlmCall.created_at.desc(), LlmCall.id.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())
