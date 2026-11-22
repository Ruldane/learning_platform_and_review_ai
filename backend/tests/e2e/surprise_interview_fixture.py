"""Horloge et profil fictifs pour le parcours Edge d’entretien surprise."""

from fastapi import APIRouter, Request

from app.core.deps import CurrentUserDep
from tests.features.applications.kit_support import add_profile
from tests.support.surprise_interview import SCRIPT as SCRIPT
from tests.support.surprise_interview import freeze_for_invite

router = APIRouter(prefix="/e2e/surprise-interview")


@router.post("/ready")
async def ready(request: Request, current: CurrentUserDep) -> dict[str, bool]:
    await add_profile(request.app, current.id)
    await freeze_for_invite(request.app, current.id)
    return {"ready": True}
