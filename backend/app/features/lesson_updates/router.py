from typing import Annotated

from fastapi import APIRouter, Depends, Path
from starlette.requests import HTTPConnection

from app.core.deps import ConfirmedUserDep, CurrentUserDep, Db
from app.core.field_paths import FieldPathsRoute
from app.features.lesson_updates.schemas import UpdateAccepted, UpdateView
from app.features.lesson_updates.service.actions import accept_update, list_updates
from app.features.lessons.service.runtime import LessonsRuntime

router = APIRouter(
    prefix="/lessons/{lesson_id}/updates", tags=["lesson_updates"], route_class=FieldPathsRoute
)
Id = Annotated[str, Path(min_length=1, max_length=36)]


def _lessons(conn: HTTPConnection) -> LessonsRuntime:
    runtime: LessonsRuntime = conn.app.state.lessons
    return runtime


Runtime = Annotated[LessonsRuntime, Depends(_lessons)]


@router.get("")
async def get_updates(lesson_id: Id, db: Db, user: CurrentUserDep) -> list[UpdateView]:
    return await list_updates(db, user.id, lesson_id)


@router.post("/{update_id}/accept", status_code=202)
async def approve_update(
    lesson_id: Id, update_id: Id, rt: Runtime, user: ConfirmedUserDep
) -> UpdateAccepted:
    return await accept_update(rt, user.id, lesson_id, update_id)
