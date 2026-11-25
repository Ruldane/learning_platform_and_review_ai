"""Program API (SPEC 3.4, 14.2; D88): list, full view, January's edits (tasks moved, added,
removed, start date), validation, `.ics` and PDF exports (D89)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response
from fastapi import status as http
from starlette.requests import HTTPConnection

from app.core.deps import CurrentUserDep, Db, PublishingDep, RuntimeDep
from app.features.program.schemas import (
    ModuleCreate,
    ModuleOut,
    ModulePatch,
    ProgramOut,
    ProgramPatch,
    ProgramSummaryOut,
    ProgramWrite,
    TaskOut,
    TaskPatch,
    ValidateOut,
    WeekCreate,
    WeekOut,
    WeekPatch,
)
from app.features.program.service import direct, editing, programs, structure, validation
from app.features.program.service.export_pdf import export_program_pdf
from app.features.program.service.ics import program_ics
from app.features.program.service.runtime import ProgramRuntime

router = APIRouter(tags=["program"])

ICS_MEDIA_TYPE = "text/calendar"
PDF_MEDIA_TYPE = "application/pdf"


def get_program_runtime(conn: HTTPConnection) -> ProgramRuntime:
    """The program opened by the lifespan (`app.state.program`)."""
    runtime: ProgramRuntime = conn.app.state.program
    return runtime


ProgramDep = Annotated[ProgramRuntime, Depends(get_program_runtime)]


@router.get("/programs", response_model=list[ProgramSummaryOut])
async def list_programs(current: CurrentUserDep, db: Db) -> list[ProgramSummaryOut]:
    return await programs.list_programs(db, current.id)


@router.post(
    "/programs/direct",
    response_model=ProgramOut,
    status_code=http.HTTP_201_CREATED,
    responses={
        404: {"description": "`goal_not_found`"},
        409: {"description": "`program_exists`"},
        422: {"description": "`invalid_start_date`, `planning_impossible` or `plan_invalid`"},
    },
)
async def write_program(body: ProgramWrite, current: CurrentUserDep, rt: ProgramDep) -> ProgramOut:
    """Writes a complete program (weeks, modules, tasks) as a draft to validate, no agent."""
    return await direct.write_program(rt, current.id, body)


@router.get("/programs/{program_id}", response_model=ProgramOut)
async def get_program(program_id: str, current: CurrentUserDep, db: Db) -> ProgramOut:
    return await programs.get_program(db, current.id, program_id)


@router.patch("/programs/{program_id}", response_model=ProgramOut)
async def patch_program(
    program_id: str, body: ProgramPatch, current: CurrentUserDep, rt: ProgramDep
) -> ProgramOut:
    return await editing.add_and_delete(rt, current.id, program_id, body)


@router.post(
    "/programs/{program_id}/weeks",
    response_model=WeekOut,
    status_code=http.HTTP_201_CREATED,
    responses={
        404: {"description": "`program_not_found`"},
        409: {"description": "`too_many_weeks`"},
    },
)
async def add_week(
    program_id: str, body: WeekCreate, current: CurrentUserDep, rt: ProgramDep
) -> WeekOut:
    """Adds a week (without a module) at the end of the program, without an agent."""
    return await structure.add_week(rt, current.id, program_id, body)


@router.patch(
    "/weeks/{week_id}",
    response_model=WeekOut,
    responses={404: {"description": "`week_not_found`"}},
)
async def patch_week(
    week_id: str, body: WeekPatch, current: CurrentUserDep, rt: ProgramDep
) -> WeekOut:
    """Edits the theme, goal or deliverable of a week, without an agent."""
    return await structure.patch_week(rt, current.id, week_id, body)


@router.post(
    "/programs/{program_id}/modules",
    response_model=ModuleOut,
    status_code=http.HTTP_201_CREATED,
    responses={
        404: {"description": "`program_not_found` or `week_not_found`"},
        409: {"description": "`week_full`"},
    },
)
async def add_module(
    program_id: str, body: ModuleCreate, current: CurrentUserDep, rt: ProgramDep
) -> ModuleOut:
    """Adds a module (without a task) to a week of the program, without an agent."""
    return await structure.add_module(rt, current.id, program_id, body)


@router.patch(
    "/modules/{module_id}",
    response_model=ModuleOut,
    responses={404: {"description": "`module_not_found`"}},
)
async def patch_module(
    module_id: str, body: ModulePatch, current: CurrentUserDep, rt: ProgramDep
) -> ModuleOut:
    """Edits the title, skills or prerequisites of a module, without an agent."""
    return await structure.patch_module(rt, current.id, module_id, body)


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
        headers={"Content-Disposition": 'attachment; filename="program.ics"'},
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
    """A4 PDF of the program (Gotenberg, no script); 502 `render_failed` if rendering fails."""
    body = await export_program_pdf(db, publishing.html_pdf, current.id, program_id)
    return Response(
        content=body,
        media_type=PDF_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="program.pdf"'},
    )
