from uuid import UUID

from fastapi import APIRouter, Request, Response

from app.agents.tools.recruitment_process_port import RecruitmentKind
from app.core.caller import ConfirmedGesture
from app.core.deps import CurrentUserDep, Db
from app.core.field_paths import FieldPathsRoute
from app.features.recruitment_process.schemas import (
    RecruitmentAnswerIn,
    RecruitmentCreate,
    RecruitmentOptions,
    RecruitmentOut,
    RecruitmentStarted,
)
from app.features.recruitment_process.service import cases, steps

router = APIRouter(
    prefix="/recruitment-processes", tags=["recruitment_process"], route_class=FieldPathsRoute
)


@router.get("/options")
async def recruitment_options(
    request: Request, db: Db, user: CurrentUserDep, response: Response
) -> RecruitmentOptions:
    response.headers["Cache-Control"] = "no-store"
    return await cases.options(request.app.state.daily.projects, db, user.id)


@router.post("", status_code=201)
async def create_recruitment_process(
    body: RecruitmentCreate, request: Request, db: Db, user: CurrentUserDep
) -> RecruitmentOut:
    return await cases.create(request.app.state.daily.projects, db, user.id, body)


@router.get("")
async def list_recruitment_processes(
    db: Db, user: CurrentUserDep, response: Response
) -> list[RecruitmentOut]:
    response.headers["Cache-Control"] = "no-store"
    return await steps.history(db, user.id)


@router.get("/{process_id}")
async def read_recruitment_process(
    process_id: UUID, db: Db, user: CurrentUserDep, response: Response
) -> RecruitmentOut:
    response.headers["Cache-Control"] = "no-store"
    return await steps.read(db, user.id, str(process_id))


@router.post("/{process_id}/steps/{kind}/answers", status_code=202, dependencies=[ConfirmedGesture])
async def answer_recruitment_step(
    process_id: UUID,
    kind: RecruitmentKind,
    body: RecruitmentAnswerIn,
    request: Request,
    user: CurrentUserDep,
) -> RecruitmentStarted:
    return await steps.submit(
        request.app.state.launcher, user.id, str(process_id), kind, body.answer
    )
