"""API des leçons et des ressources (SPEC 3.5, 3.6, 14.2 ; D91) : leçon et son PDF, Bibliothèque
filtrable, statut de lecture d'une ressource, copie locale d'un PDF libre. Hors 14.2 :
`GET /programs/{id}/lessons` (liste d'un programme) et `GET /resources/{id}/file`. Les fichiers
ne sont servis qu'à leur propriétaire (404 sinon)."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response
from starlette.requests import HTTPConnection

from app.core.deps import CurrentUserDep, Db
from app.features.lessons.schemas import (
    LessonOut,
    LessonSummaryOut,
    ResourceOut,
    ResourcePatch,
    ResourceStatus,
    ResourceType,
)
from app.features.lessons.service import lessons, resources
from app.features.lessons.service.runtime import LessonsRuntime

router = APIRouter(tags=["lessons"])

PDF_MEDIA_TYPE = "application/pdf"
_PDF_RESPONSE: dict[int | str, dict[str, Any]] = {
    200: {"content": {PDF_MEDIA_TYPE: {"schema": {"type": "string", "format": "binary"}}}}
}


def get_lessons_runtime(conn: HTTPConnection) -> LessonsRuntime:
    """Les leçons ouvertes par le lifespan (`app.state.lessons`)."""
    runtime: LessonsRuntime = conn.app.state.lessons
    return runtime


LessonsDep = Annotated[LessonsRuntime, Depends(get_lessons_runtime)]


def _pdf(body: bytes, filename: str) -> Response:
    return Response(
        content=body,
        media_type=PDF_MEDIA_TYPE,
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/programs/{program_id}/lessons", response_model=list[LessonSummaryOut])
async def list_program_lessons(
    program_id: str, current: CurrentUserDep, db: Db
) -> list[LessonSummaryOut]:
    return await lessons.list_lessons(db, current.id, program_id)


@router.get("/lessons/{lesson_id}", response_model=LessonOut)
async def get_lesson(lesson_id: str, current: CurrentUserDep, db: Db) -> LessonOut:
    return await lessons.get_lesson(db, current.id, lesson_id)


@router.get("/lessons/{lesson_id}/pdf", response_class=Response, responses=_PDF_RESPONSE)
async def get_lesson_pdf(
    lesson_id: str, current: CurrentUserDep, db: Db, rt: LessonsDep
) -> Response:
    """PDF A4 de la leçon ; 404 `lesson_pdf_missing` tant qu'il n'est pas produit."""
    _, body = await lessons.lesson_pdf(db, rt.storage, current.id, lesson_id)
    return _pdf(body, "lecon.pdf")


@router.get("/resources", response_model=list[ResourceOut])
async def list_resources(
    current: CurrentUserDep,
    db: Db,
    program_id: Annotated[str | None, Query(min_length=1, max_length=36)] = None,
    type: ResourceType | None = None,
    lang: Annotated[str | None, Query(min_length=2, max_length=8)] = None,
    status: ResourceStatus | None = None,
) -> list[ResourceOut]:
    """Bibliothèque : ressources de l'utilisateur, les plus récentes d'abord, filtrées par
    programme, type, langue et statut."""
    f = resources.ResourceFilter(program_id=program_id, type=type, lang=lang, status=status)
    return await resources.list_resources(db, current.id, f)


@router.patch("/resources/{resource_id}", response_model=ResourceOut)
async def patch_resource(
    resource_id: str, body: ResourcePatch, current: CurrentUserDep, db: Db
) -> ResourceOut:
    return await resources.patch_resource(db, current.id, resource_id, body)


@router.get("/resources/{resource_id}/file", response_class=Response, responses=_PDF_RESPONSE)
async def get_resource_file(
    resource_id: str, current: CurrentUserDep, db: Db, rt: LessonsDep
) -> Response:
    """Copie locale du PDF libre ; 404 `resource_file_missing` s'il n'y en a pas."""
    body = await resources.resource_file(db, rt.storage, current.id, resource_id)
    return _pdf(body, "ressource.pdf")
