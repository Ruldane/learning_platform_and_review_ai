"""API du brief du matin (SPEC 14.2, P12, D162) : `GET /brief/today` rend le brief du jour local
de l'utilisatrice et le crée s'il manque (à l'ouverture, quelle que soit l'heure). Il n'attend
jamais un agent : le conseil et la ressource arrivent ensuite (`advice_status` `pending`, à
relire). Au nom de l'utilisatrice courante."""

from typing import Annotated

from fastapi import APIRouter, Depends
from starlette.requests import HTTPConnection

from app.core.deps import CurrentUserDep
from app.features.brief.schemas import BriefOut
from app.features.brief.service.ensure import ensure_today
from app.features.brief.service.runtime import BriefRuntime

router = APIRouter(prefix="/brief", tags=["brief"])


def get_brief_runtime(conn: HTTPConnection) -> BriefRuntime:
    """Le brief ouvert par le lifespan (`app.state.daily.brief`)."""
    runtime: BriefRuntime = conn.app.state.daily.brief
    return runtime


BriefDep = Annotated[BriefRuntime, Depends(get_brief_runtime)]


@router.get("/today", response_model=BriefOut)
async def get_today(current: CurrentUserDep, rt: BriefDep) -> BriefOut:
    """Le brief du jour local, créé s'il manque (`origin` « opening »)."""
    brief, _created = await ensure_today(rt, current.id, origin="opening")
    return brief
