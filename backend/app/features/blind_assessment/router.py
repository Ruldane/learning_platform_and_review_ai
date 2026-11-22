"""Épreuves comparatives du compte courant."""

from uuid import UUID

from fastapi import APIRouter, Request, Response

from app.core.deps import CurrentUserDep, Db
from app.core.field_paths import FieldPathsRoute
from app.features.blind_assessment.schemas import BlindCreate, BlindOptions, BlindOut, BlindStarted
from app.features.blind_assessment.service import comparisons

router = APIRouter(
    prefix="/blind-assessments", tags=["blind_assessment"], route_class=FieldPathsRoute
)


@router.get("/options")
async def get_blind_options(
    request: Request, user: CurrentUserDep, response: Response
) -> BlindOptions:
    response.headers["Cache-Control"] = "no-store"
    return await comparisons.options(request.app.state.career.cv, user.id)


@router.get("")
async def list_blind(db: Db, user: CurrentUserDep, response: Response) -> list[BlindOut]:
    response.headers["Cache-Control"] = "no-store"
    return await comparisons.history(db, user.id)


@router.post("", status_code=201)
async def create_blind(body: BlindCreate, db: Db, user: CurrentUserDep) -> BlindOut:
    return await comparisons.create(db, user.id, body)


@router.get("/{assessment_id}")
async def read_blind(
    assessment_id: UUID, db: Db, user: CurrentUserDep, response: Response
) -> BlindOut:
    response.headers["Cache-Control"] = "no-store"
    return await comparisons.read(db, user.id, str(assessment_id))


@router.post("/{assessment_id}/evaluate", status_code=202)
async def evaluate_blind(
    assessment_id: UUID, request: Request, user: CurrentUserDep
) -> BlindStarted:
    return await comparisons.evaluate(request.app.state.launcher, user.id, str(assessment_id))
