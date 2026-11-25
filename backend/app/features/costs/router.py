"""AI costs (SPEC 11.5, phase 9): the report by day, by feature, by agent and by model, and the
call log. On behalf of the current user; a 422 names the fields without ever echoing the value
received."""

from typing import Annotated, Literal

from fastapi import APIRouter, Query
from pydantic import BeforeValidator

from app.core.deps import CurrentUserDep, Db
from app.core.field_paths import FieldPathsRoute
from app.features.costs.schemas import AgentCallPage, CostsReport
from app.features.costs.service import costs_report, list_calls

router = APIRouter(prefix="/costs", tags=["costs"], route_class=FieldPathsRoute)


def _days_from_query(value: object) -> object:
    """A query parameter arrives as text: pydantic does not read "7" as the integer 7 for a
    `Literal`. Only ASCII digits are converted; anything else stays as is, hence rejected."""
    if isinstance(value, str) and value.isascii() and value.isdigit():
        return int(value)
    return value


Days = Annotated[Literal[7, 30, 90], BeforeValidator(_days_from_query)]


@router.get(
    "",
    response_model=CostsReport,
    responses={422: {"description": "`details.fields`: `days` (not 7, 30 or 90)"}},
)
async def get_costs(
    current: CurrentUserDep, db: Db, days: Annotated[Days, Query()] = 30
) -> CostsReport:
    """Costs over the last 7, 30 or 90 days (days in the user's time zone, today included),
    aggregated from the logged calls, at the prices of each call. Any other duration: 422
    (`details.fields`: `days`)."""
    return await costs_report(db, current.id, days)


@router.get(
    "/calls",
    response_model=AgentCallPage,
    responses={422: {"description": "`details.fields`: `before` (unreadable cursor) or `limit`"}},
)
async def get_calls(
    current: CurrentUserDep,
    db: Db,
    before: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    agent: Annotated[str | None, Query(max_length=64)] = None,
    graph: Annotated[str | None, Query(max_length=64)] = None,
) -> AgentCallPage:
    """The agent log: calls newest first, `limit` per page (50 by default). `before` is the
    `next_before` cursor of the previous page; `agent` and `graph` filter. No prompt
    content."""
    return await list_calls(db, current.id, before=before, limit=limit, agent=agent, graph=graph)
