"""Lessons and resources API (SPEC 3.5, 3.6, 14.2; D91): a lesson and its PDF, filterable
Library, reading status of a resource, local copy of a free PDF. Outside 14.2:
`GET /programs/{id}/lessons` (a program's list) and `GET /resources/{id}/file`. Files are only
served to their owner (404 otherwise)."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response, status
from starlette.requests import HTTPConnection

from app.core.caller import CallerDep
from app.core.deps import CurrentUserDep, Db
from app.core.errors import AppError
from app.core.played import PLAY_CONTEXT
from app.features.lessons.schemas import (
    LessonOut,
    LessonPatch,
    LessonSummaryOut,
    LessonWriteIn,
    ResourceOut,
    ResourcePatch,
    ResourceStatus,
    ResourceType,
)
from app.features.lessons.service import direct, lessons, resources
from app.features.lessons.service.runtime import LessonsRuntime

router = APIRouter(tags=["lessons"])

PDF_MEDIA_TYPE = "application/pdf"
_PDF_RESPONSE: dict[int | str, dict[str, Any]] = {
    200: {"content": {PDF_MEDIA_TYPE: {"schema": {"type": "string", "format": "binary"}}}}
}


def get_lessons_runtime(conn: HTTPConnection) -> LessonsRuntime:
    """The lessons runtime opened by the lifespan (`app.state.lessons`)."""
    runtime: LessonsRuntime = conn.app.state.lessons
    return runtime


LessonsDep = Annotated[LessonsRuntime, Depends(get_lessons_runtime)]


def _pdf(body: bytes, filename: str, *, third_party: bool = False) -> Response:
    """Our lesson PDF opens in the browser (`inline`). A third-party PDF (local copy of a
    resource) is downloaded (`attachment`) and sandboxed (CSP `sandbox`): never displayed on the
    application's origin (D97)."""
    disposition = "attachment" if third_party else "inline"
    headers = {
        "Content-Disposition": f'{disposition}; filename="{filename}"',
        "X-Content-Type-Options": "nosniff",
    }
    if third_party:
        headers["Content-Security-Policy"] = "sandbox"
    return Response(content=body, media_type=PDF_MEDIA_TYPE, headers=headers)


@router.get("/programs/{program_id}/lessons", response_model=list[LessonSummaryOut])
async def list_program_lessons(
    program_id: str, current: CurrentUserDep, db: Db
) -> list[LessonSummaryOut]:
    return await lessons.list_lessons(db, current.id, program_id)


@router.get("/lessons/{lesson_id}", response_model=LessonOut)
async def get_lesson(lesson_id: str, current: CurrentUserDep, db: Db) -> LessonOut:
    return await lessons.get_lesson(db, current.id, lesson_id)


@router.post(
    "/modules/{module_id}/lesson",
    response_model=LessonOut,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        404: {"description": "`module_not_found`"},
        409: {
            "description": "`lesson_exists`, `lesson_generating`, `module_skipped`"
            " or `module_without_lesson`"
        },
    },
)
async def write_lesson(
    module_id: str, body: LessonWriteIn, current: CurrentUserDep, rt: LessonsDep, caller: CallerDep
) -> LessonOut:
    """Submits the given Markdown to the Factory and returns its verification session."""
    return await direct.write_lesson(rt, current.id, module_id, body, is_mcp=caller.kind == "mcp")


@router.patch(
    "/lessons/{lesson_id}",
    response_model=LessonOut,
    responses={
        202: {"model": LessonOut, "description": "Draft submitted for verification."},
        404: {"description": "`lesson_not_found`"},
        409: {"description": "`lesson_not_ready` or `lesson_generating`"},
    },
)
async def patch_lesson(
    lesson_id: str,
    body: LessonPatch,
    current: CurrentUserDep,
    rt: LessonsDep,
    caller: CallerDep,
    response: Response,
) -> LessonOut:
    """Submits a title or text edit. Adding resources alone is immediate."""
    play = PLAY_CONTEXT.get()
    if play and play.graph == "lesson_factory" and body.title is None and body.markdown is None:
        raise AppError(
            "lesson_draft_required",
            "To play the verification, provide a lesson title or text.",
            422,
        )
    result, submitted = await direct.patch_lesson(
        rt, current.id, lesson_id, body, is_mcp=caller.kind == "mcp"
    )
    if submitted:
        response.status_code = status.HTTP_202_ACCEPTED
    return result


@router.get("/lessons/{lesson_id}/pdf", response_class=Response, responses=_PDF_RESPONSE)
async def get_lesson_pdf(
    lesson_id: str, current: CurrentUserDep, db: Db, rt: LessonsDep
) -> Response:
    """A4 PDF of the lesson; 404 `lesson_pdf_missing` until it is produced."""
    _, body = await lessons.lesson_pdf(db, rt.storage, current.id, lesson_id)
    return _pdf(body, "lesson.pdf")


@router.get("/resources", response_model=list[ResourceOut])
async def list_resources(
    current: CurrentUserDep,
    db: Db,
    program_id: Annotated[str | None, Query(min_length=1, max_length=36)] = None,
    type: ResourceType | None = None,
    lang: Annotated[str | None, Query(min_length=2, max_length=8)] = None,
    status: ResourceStatus | None = None,
) -> list[ResourceOut]:
    """Library: the user's resources, most recent first, filtered by program, type, language
    and status."""
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
    """Local copy of the free PDF, as a download; 404 `resource_file_missing` if there is
    none."""
    body = await resources.resource_file(db, rt.storage, current.id, resource_id)
    return _pdf(body, "resource.pdf", third_party=True)
