from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import ColumnElement, Row, and_, or_, select
from sqlalchemy.orm import InstrumentedAttribute

from app.db.models.agents import LlmCall
from app.db.repository import UserScopedRepository

# The columns the report and the log read: neither `user_id` nor `updated_at`, and light
# rows (no entities in the session) for the report's 90 days.
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


def _matches(column: InstrumentedAttribute[str | None], value: str) -> ColumnElement[bool]:
    """Equality; the empty value means "none": the cost report files under the key `""` the
    calls whose agent or graph is NULL, and the log finds them again with that same key."""
    return or_(column.is_(None), column == "") if value == "" else column == value


class LlmCallRepository(UserScopedRepository[LlmCall]):
    """Reads the call log (`llm_calls`) on behalf of a single user."""

    model = LlmCall

    async def since(self, start_utc: datetime) -> Sequence[Row[*tuple[Any, ...]]]:
        """Calls made from `start_utc` (inclusive), oldest first."""
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
        """`limit` calls, newest first, strictly before the cursor `(created_at, id)`
        if there is one; `agent` and `graph` filter."""
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
            stmt = stmt.where(_matches(LlmCall.agent, agent))
        if graph is not None:
            stmt = stmt.where(_matches(LlmCall.graph, graph))
        stmt = stmt.order_by(LlmCall.created_at.desc(), LlmCall.id.desc()).limit(limit)
        return (await self.session.execute(stmt)).all()
