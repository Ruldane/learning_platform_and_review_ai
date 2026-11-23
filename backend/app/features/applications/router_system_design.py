from fastapi import APIRouter

from app.core.deps import CurrentUserDep
from app.features.applications.router import ApplicationsDep, Id
from app.features.applications.schemas_system_design import DesignState
from app.features.applications.service.system_design import read

router = APIRouter(tags=["interviews"])


@router.get("/system-design")
async def current_design(current: CurrentUserDep, rt: ApplicationsDep) -> DesignState | None:
    return await read(rt, current.id)


@router.get("/interviews/{interview_id}/design")
async def get_design(
    interview_id: Id, current: CurrentUserDep, rt: ApplicationsDep
) -> DesignState | None:
    return await read(rt, current.id, interview_id)
