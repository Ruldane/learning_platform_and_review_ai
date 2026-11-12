"""API du programme (SPEC 3.4, 14.2 ; D88) : liste, vue complète, modifications de January
(tâches déplacées, ajoutées, supprimées, date de début), validation, exports `.ics` et PDF (D89)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response
from fastapi import status as http
from starlette.requests import HTTPConnection

from app.core.deps import CurrentUserDep, Db, PublishingDep, RuntimeDep
from app.features.program.schemas import (
    ProgramOut,
    ProgramPatch,
    ProgramSummaryOut,
    TaskOut,
    TaskPatch,
    ValidateOut,
)
from app.features.program.service import editing, programs, validation
from app.features.program.service.export_pdf import export_program_pdf
from app.features.program.service.ics import program_ics
from app.features.program.service.runtime import ProgramRuntime

router = APIRouter(tags=["program"])

ICS_MEDIA_TYPE = "text/calendar"
PDF_MEDIA_TYPE = "application/pdf"


def get_program_runtime(conn: HTTPConnection) -> ProgramRuntime:
    """Le programme ouvert par le lifespan (`app.state.program`)."""
    runtime: ProgramRuntime = conn.app.state.program
    return runtime


ProgramDep = Annotated[ProgramRuntime, Depends(get_program_runtime)]


@router.get("/programs", response_model=list[ProgramSummaryOut])
async def list_programs(current: CurrentUserDep, db: Db) -> list[ProgramSummaryOut]:
    return await programs.list_programs(db, current.id)


@router.get("/programs/{program_id}", response_model=ProgramOut)
async def get_program(program_id: str, current: CurrentUserDep, db: Db) -> ProgramOut:
    return await programs.get_program(db, current.id, program_id)


@router.patch("/programs/{program_id}", response_model=ProgramOut)
async def patch_program(
    program_id: str, body: ProgramPatch, current: CurrentUserDep, rt: ProgramDep
) -> ProgramOut:
    return await editing.add_and_delete(rt, current.id, program_id, body)


@router.post(
    "/programs/{program_id}/validate",
    status_code=http.HTTP_202_ACCEPTED,
    response_model=ValidateOut,
)
async def validate_program(
    program_id: str, current: CurrentUserDep, runtime: RuntimeDep, rt: ProgramDep
) -> ValidateOut:
    return await validation.request_validation(runtime, rt, current.id, program_id)


@router.patch("/tasks/{task_id}", response_model=TaskOut)
async def patch_task(
    task_id: str, body: TaskPatch, current: CurrentUserDep, rt: ProgramDep
) -> TaskOut:
    return await editing.move_or_edit_task(rt, current.id, task_id, body)


@router.get(
    "/programs/{program_id}/export.ics",
    response_class=Response,
    responses={200: {"content": {ICS_MEDIA_TYPE: {"schema": {"type": "string"}}}}},
)
async def export_ics(program_id: str, current: CurrentUserDep, db: Db) -> Response:
    body = program_ics(await programs.get_program(db, current.id, program_id))
    return Response(
        content=body,
        media_type=f"{ICS_MEDIA_TYPE}; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="programme.ics"'},
    )


@router.get(
    "/programs/{program_id}/export.pdf",
    response_class=Response,
    responses={
        200: {"content": {PDF_MEDIA_TYPE: {"schema": {"type": "string", "format": "binary"}}}}
    },
)
async def export_pdf(
    program_id: str, current: CurrentUserDep, db: Db, publishing: PublishingDep
) -> Response:
    """PDF A4 du programme (Gotenberg, sans script) ; 502 `render_failed` si le rendu échoue."""
    body = await export_program_pdf(db, publishing.html_pdf, current.id, program_id)
    return Response(
        content=body,
        media_type=PDF_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="programme.pdf"'},
    )
