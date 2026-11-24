"""Critical reading on demand, outside the publication cycle."""

from fastapi import APIRouter, Request

from app.core.caller import ConfirmedGesture
from app.core.deps import CurrentUserDep, Db
from app.core.field_paths import FieldPathsRoute
from app.features.lesson_hunt.schemas import HuntAnswers, HuntCreate, HuntOut, HuntStarted
from app.features.lesson_hunt.service.hunts import get_hunt, start_hunt, submit_answers

router = APIRouter(prefix="/lesson-hunts", tags=["lesson_hunt"], route_class=FieldPathsRoute)


@router.post("", status_code=202, dependencies=[ConfirmedGesture])
async def create_hunt(body: HuntCreate, request: Request, current: CurrentUserDep) -> HuntStarted:
    return await start_hunt(request.app.state.launcher, current.id, body.lesson_id)


@router.get("/{hunt_id}")
async def read_hunt(hunt_id: str, current: CurrentUserDep, db: Db) -> HuntOut:
    return await get_hunt(db, current.id, hunt_id)


@router.post("/{hunt_id}/answers", status_code=202, dependencies=[ConfirmedGesture])
async def answer_hunt(
    hunt_id: str, body: HuntAnswers, request: Request, current: CurrentUserDep
) -> HuntStarted:
    return await submit_answers(request.app.state.launcher, current.id, hunt_id, body)
