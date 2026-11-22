"""Actions d'arborescence et onglets des séances Python."""

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
    """Crée un fichier à partir de la version lue de la séance."""
    return await ide.create_project_file(session_id, body)


@router.patch("/files")
async def rename_project_file(session_id: Id, body: ProjectFileRename, ide: Ide) -> IdeSessionOut:
    """Renomme un fichier du projet et adapte l'entrée et les onglets."""
    return await ide.rename_project_file(session_id, body)


@router.delete("/files")
async def remove_project_file(session_id: Id, body: ProjectFileRemove, ide: Ide) -> IdeSessionOut:
    """Retire un fichier du projet et referme son onglet."""
    return await ide.remove_project_file(session_id, body)


@router.put("/tabs")
async def save_project_tabs(session_id: Id, body: ProjectTabsState, ide: Ide) -> ProjectTabsState:
    """Garde les onglets de l'interface pour la prochaine ouverture de la séance."""
    return await ide.save_project_tabs(session_id, body)
