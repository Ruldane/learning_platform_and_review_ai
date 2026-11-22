from typing import Annotated

from fastapi import APIRouter, Depends
from starlette.requests import HTTPConnection

from app.core.deps import CurrentUserDep, Db
from app.core.field_paths import FieldPathsRoute
from app.features.study_return import service
from app.features.study_return.schemas import StudyReturnOut, StudyReturnReminder
from app.features.study_return.service import StudyReturnRuntime

router = APIRouter(prefix="/study-return", tags=["study_return"], route_class=FieldPathsRoute)


async def get_runtime(conn: HTTPConnection) -> StudyReturnRuntime:
    runtime: StudyReturnRuntime | None = getattr(conn.app.state, "study_return", None)
    if runtime is None:
        runtime = StudyReturnRuntime(conn.app.state.study, conn.app.state.quiz)
        conn.app.state.study_return = runtime
    return runtime


StudyReturnDep = Annotated[StudyReturnRuntime, Depends(get_runtime)]


@router.get("")
async def get(db: Db, rt: StudyReturnDep, user: CurrentUserDep) -> StudyReturnOut:
    return await service.get(rt, db, user.id)


@router.post("/prepare")
async def prepare(rt: StudyReturnDep, user: CurrentUserDep) -> StudyReturnOut:
    return await service.prepare(rt, user.id)


@router.put("/reminder")
async def reminder(
    action: StudyReturnReminder, rt: StudyReturnDep, user: CurrentUserDep
) -> StudyReturnOut:
    return await service.set_reminder(rt, user.id, action.day)


@router.post("/start")
async def start(rt: StudyReturnDep, user: CurrentUserDep) -> StudyReturnOut:
    return await service.start(rt, user.id)
