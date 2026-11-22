from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from starlette.requests import HTTPConnection

from app.core.deps import CurrentUserDep, Db, InterfaceUserDep
from app.core.field_paths import FieldPathsRoute
from app.features.project_handoffs import service
from app.features.project_handoffs.schemas import (
    ProjectHandoffApproval,
    ProjectHandoffDraft,
    ProjectHandoffOut,
    ProjectHandoffPreview,
    ProjectHandoffSource,
    ProjectHandoffSummary,
)
from app.features.projects.service.runtime import ProjectsRuntime

_PRIVATE = {"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"}
_EXPORT_MEDIA = "text/markdown"


def _private(response: Response) -> None:
    response.headers.update(_PRIVATE)


def _projects(conn: HTTPConnection) -> ProjectsRuntime:
    runtime: ProjectsRuntime = conn.app.state.daily.projects
    return runtime


Projects = Annotated[ProjectsRuntime, Depends(_projects)]

router = APIRouter(
    prefix="/project-handoffs",
    tags=["project_handoffs"],
    route_class=FieldPathsRoute,
    dependencies=[Depends(_private)],
)


@router.get("/source/{project_id}")
async def read_source(
    project_id: UUID, user: CurrentUserDep, db: Db, rt: Projects
) -> ProjectHandoffSource:
    return await service.source(rt, db, user.id, project_id)


@router.post("/preview")
async def preview_guide(
    body: ProjectHandoffDraft, user: CurrentUserDep, db: Db, rt: Projects
) -> ProjectHandoffPreview:
    return await service.preview(rt, db, user.id, body)


@router.get("")
async def list_handoffs(user: CurrentUserDep, db: Db) -> list[ProjectHandoffSummary]:
    return await service.list_handoffs(db, user.id)


@router.post("", status_code=201)
async def approve_guide(
    body: ProjectHandoffApproval, user: CurrentUserDep, db: Db, rt: Projects
) -> ProjectHandoffOut:
    return await service.approve(rt, db, user.id, body)


@router.get("/{handoff_id}")
async def read_handoff(handoff_id: UUID, user: CurrentUserDep, db: Db) -> ProjectHandoffOut:
    return await service.read(db, user.id, handoff_id)


@router.get(
    "/{handoff_id}/export",
    response_class=Response,
    responses={200: {"content": {_EXPORT_MEDIA: {"schema": {"type": "string"}}}}},
)
async def export_handoff(handoff_id: UUID, user: InterfaceUserDep, db: Db) -> Response:
    guide = await service.read(db, user.id, handoff_id)
    return Response(
        guide.markdown,
        media_type=_EXPORT_MEDIA,
        headers={
            **_PRIVATE,
            "Content-Disposition": 'attachment; filename="guide-de-reprise.md"',
        },
    )
