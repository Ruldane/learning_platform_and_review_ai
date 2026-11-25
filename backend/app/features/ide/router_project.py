"""File-tree actions and tabs of Python sessions."""

from fastapi import APIRouter

from app.core.field_paths import FieldPathsRoute
from app.features.ide.router_deps import Id, Ide
from app.features.ide.schemas import IdeSessionOut
from app.features.ide.schemas_project import (
    ProjectFileCreate,
    ProjectFileRemove,
    ProjectFileRename,
    ProjectTabsState,
)

router = APIRouter(prefix="/sessions/{session_id}", route_class=FieldPathsRoute)


@router.post("/files", status_code=201)
async def add_project_file(session_id: Id, body: ProjectFileCreate, ide: Ide) -> IdeSessionOut:
    """Creates a file from the session version that was read."""
    return await ide.create_project_file(session_id, body)


@router.patch("/files")
async def rename_project_file(session_id: Id, body: ProjectFileRename, ide: Ide) -> IdeSessionOut:
    """Renames a project file and updates the entry and tabs."""
    return await ide.rename_project_file(session_id, body)


@router.delete("/files")
async def remove_project_file(session_id: Id, body: ProjectFileRemove, ide: Ide) -> IdeSessionOut:
    """Removes a file from the project and closes its tab."""
    return await ide.remove_project_file(session_id, body)


@router.put("/tabs")
async def save_project_tabs(session_id: Id, body: ProjectTabsState, ide: Ide) -> ProjectTabsState:
    """Keeps the interface tabs for the next time the session is opened."""
    return await ide.save_project_tabs(session_id, body)
