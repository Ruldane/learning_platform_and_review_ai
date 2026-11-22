"""Accès aux mini-cours tirés des articles du compte."""

from fastapi import APIRouter, Request

from app.core.deps import CurrentUserDep, Db
from app.core.field_paths import FieldPathsRoute
from app.features.paper_lab.schemas import (
    PaperLabCreate,
    PaperLabOut,
    PaperLabStarted,
    PaperLabSummary,
)
from app.features.paper_lab.service.labs import list_labs, read_lab, start_lab

router = APIRouter(prefix="/paper-labs", tags=["paper_lab"], route_class=FieldPathsRoute)


@router.get("")
async def list_course_sources(current: CurrentUserDep, db: Db) -> list[PaperLabSummary]:
    return await list_labs(db, current.id)


@router.post("", status_code=202)
async def create_course(
    body: PaperLabCreate, request: Request, current: CurrentUserDep
) -> PaperLabStarted:
    return await start_lab(request.app.state.launcher, current.id, str(body.url))


@router.get("/{lab_id}")
async def get_course(lab_id: str, current: CurrentUserDep, db: Db) -> PaperLabOut:
    return await read_lab(db, current.id, lab_id)
