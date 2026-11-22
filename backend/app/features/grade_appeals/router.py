from uuid import UUID

from fastapi import APIRouter, Request, Response

from app.core.caller import JanuaryOnly
from app.core.deps import CurrentUserDep, Db
from app.core.field_paths import FieldPathsRoute
from app.features.grade_appeals.schemas import (
    GradeAppealCreate,
    GradeAppealCriterion,
    GradeAppealDecisionIn,
    GradeAppealOut,
    GradeAppealProject,
    GradeAppealStarted,
)
from app.features.grade_appeals.service import sources, workflow

router = APIRouter(prefix="/grade-appeals", tags=["grade_appeals"], route_class=FieldPathsRoute)


@router.get("/projects")
async def list_appeal_projects(
    request: Request, db: Db, user: CurrentUserDep, response: Response
) -> list[GradeAppealProject]:
    response.headers["Cache-Control"] = "no-store"
    return await sources.projects(request.app.state.daily.projects, db, user.id)


@router.get("/projects/{project_id}/criteria")
async def list_appeal_criteria(
    project_id: UUID, request: Request, db: Db, user: CurrentUserDep, response: Response
) -> list[GradeAppealCriterion]:
    response.headers["Cache-Control"] = "no-store"
    return await sources.criteria(request.app.state.daily.projects, db, user.id, str(project_id))


@router.post("", status_code=201)
async def create_grade_appeal(
    body: GradeAppealCreate, request: Request, db: Db, user: CurrentUserDep
) -> GradeAppealOut:
    return await sources.create(request.app.state.daily.projects, db, user.id, body)


@router.get("")
async def list_grade_appeals(
    db: Db, user: CurrentUserDep, response: Response
) -> list[GradeAppealOut]:
    response.headers["Cache-Control"] = "no-store"
    return await workflow.history(db, user.id)


@router.get("/{appeal_id}")
async def read_grade_appeal(
    appeal_id: UUID, db: Db, user: CurrentUserDep, response: Response
) -> GradeAppealOut:
    response.headers["Cache-Control"] = "no-store"
    return await workflow.read(db, user.id, str(appeal_id))


@router.post("/{appeal_id}/review", status_code=202)
async def review_grade_appeal(
    appeal_id: UUID, request: Request, user: CurrentUserDep
) -> GradeAppealStarted:
    return await workflow.review(request.app.state.launcher, user.id, str(appeal_id))


@router.post("/{appeal_id}/decision", dependencies=[JanuaryOnly])
async def decide_grade_appeal(
    appeal_id: UUID, body: GradeAppealDecisionIn, db: Db, user: CurrentUserDep
) -> GradeAppealOut:
    return await workflow.decide(db, user.id, str(appeal_id), body.decision)
