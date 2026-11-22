from uuid import UUID

from fastapi import APIRouter, Depends, Response

from app.core.deps import CurrentUserDep, Db
from app.features.lesson_variants import service
from app.features.lesson_variants.schemas import (
    LessonVariantCreate,
    LessonVariantOut,
    LessonVariantSummary,
)


def _private(response: Response) -> None:
    response.headers["Cache-Control"] = "private, no-store"


router = APIRouter(
    prefix="/lesson-variants", tags=["lesson_variants"], dependencies=[Depends(_private)]
)


@router.get("")
async def list_editions(user: CurrentUserDep, db: Db) -> list[LessonVariantSummary]:
    return await service.list_editions(db, user.id)


@router.post("", status_code=201)
async def create_edition(
    body: LessonVariantCreate, user: CurrentUserDep, db: Db
) -> LessonVariantOut:
    return await service.prepare(db, user.id, str(body.lesson_id))


@router.get("/{edition_id}")
async def read_edition(edition_id: UUID, user: CurrentUserDep, db: Db) -> LessonVariantOut:
    return await service.read(db, user.id, str(edition_id))
