"""Morning brief API (SPEC 14.2, P12, D162): `GET /brief/today` returns the user's brief for her
local day and creates it if missing (on opening, whatever the time). It never waits for an
agent: the advice and the resource arrive later (`advice_status` `pending`, read again). On
behalf of the current user."""

from typing import Annotated

from fastapi import APIRouter, Depends
from starlette.requests import HTTPConnection

from app.core.deps import CurrentUserDep
from app.features.brief.schemas import BriefOut
from app.features.brief.service.ensure import ensure_today
from app.features.brief.service.runtime import BriefRuntime

router = APIRouter(prefix="/brief", tags=["brief"])


def get_brief_runtime(conn: HTTPConnection) -> BriefRuntime:
    """The brief opened by the lifespan (`app.state.daily.brief`)."""
    runtime: BriefRuntime = conn.app.state.daily.brief
    return runtime


BriefDep = Annotated[BriefRuntime, Depends(get_brief_runtime)]


@router.get("/today", response_model=BriefOut)
async def get_today(current: CurrentUserDep, rt: BriefDep) -> BriefOut:
    """The brief for the local day, created if missing (`origin` "opening")."""
    brief, _created = await ensure_today(rt, current.id, origin="opening")
    return brief
