from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import Row, and_, or_, select

from app.db.models.agents import LlmCall
from app.db.repository import UserScopedRepository

# Les colonnes que lisent le rapport et le journal : ni `user_id`, ni `updated_at`, et des
# lignes légères (pas d'entités dans la session) pour les 90 jours du rapport.
_SINCE_COLUMNS = (
    LlmCall.created_at,
    LlmCall.graph,
    LlmCall.agent,
    LlmCall.provider,
    LlmCall.model,
    LlmCall.tokens_in,
    LlmCall.tokens_out,
    LlmCall.cost_usd,
    LlmCall.estimated,
)
_PAGE_COLUMNS = (
    LlmCall.id,
    *_SINCE_COLUMNS,
    LlmCall.session_id,
    LlmCall.latency_ms,
)


class LlmCallRepository(UserScopedRepository[LlmCall]):
    """Lecture du journal des appels (`llm_calls`), au nom d'une seule utilisatrice."""

    model = LlmCall

    async def since(self, start_utc: datetime) -> Sequence[Row[*tuple[Any, ...]]]:
        """Les appels faits à partir de `start_utc` (inclus), du plus ancien au plus récent."""
        stmt = (
            select(*_SINCE_COLUMNS)
            .where(LlmCall.user_id == self.user_id, LlmCall.created_at >= start_utc)
            .order_by(LlmCall.created_at, LlmCall.id)
        )
        return (await self.session.execute(stmt)).all()

    async def page(
        self,
        *,
        before: tuple[datetime, str] | None,
        limit: int,
        agent: str | None,
        graph: str | None,
    ) -> Sequence[Row[*tuple[Any, ...]]]:
        """`limit` appels du plus récent au plus ancien, strictement avant le curseur
        `(created_at, id)` s'il y en a un ; `agent` et `graph` filtrent."""
        stmt = select(*_PAGE_COLUMNS).where(LlmCall.user_id == self.user_id)
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
        return (await self.session.execute(stmt)).all()
