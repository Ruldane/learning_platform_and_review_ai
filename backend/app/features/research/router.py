"""Web research API, outside SPEC 14.2 (D76): the month's Brave counter and a session's sources.
Searching and reading themselves go through the agents (`web_*` tools, phase 3.7)."""

from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from starlette.requests import HTTPConnection

from app.core.deps import CurrentUserDep, Db
from app.features.research.schemas import BraveUsageOut, SearchUsageOut, SourceOut
from app.features.research.service.reading import list_sources
from app.features.research.service.runtime import ResearchRuntime
from app.features.research.service.usage import brave_usage

router = APIRouter(prefix="/research", tags=["research"])


def get_research_runtime(conn: HTTPConnection) -> ResearchRuntime:
    """The web research opened by the lifespan (`app.state.research`)."""
    runtime: ResearchRuntime = conn.app.state.research
    return runtime


ResearchDep = Annotated[ResearchRuntime, Depends(get_research_runtime)]


@router.get("/usage", response_model=SearchUsageOut)
async def get_usage(current: CurrentUserDep, db: Db, research: ResearchDep) -> SearchUsageOut:
    usage = await brave_usage(db, research.keys, current.id, research.now())
    return SearchUsageOut(brave=BraveUsageOut(**asdict(usage)))


@router.get("/sources", response_model=list[SourceOut])
async def get_sources(
    current: CurrentUserDep,
    db: Db,
    session_id: Annotated[str, Query(min_length=1, max_length=36)],
) -> list[SourceOut]:
    rows = await list_sources(db, current.id, session_id)
    return [SourceOut.model_validate(row) for row in rows]
