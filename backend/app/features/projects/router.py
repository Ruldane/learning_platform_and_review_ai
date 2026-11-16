"""API des mini projets preuves (SPEC 14.2, P1 à P3, P19, D166) : Portfolio, projet, rendu (202,
l'évaluation tourne en tâche de fond), captures, brouillons retouchés, entrée au profil maître et
nouvel essai de l'énoncé. Toutes au nom de l'utilisatrice courante (404 sur le projet d'une autre) ;
une 422 nomme les champs, sans jamais recopier le rendu."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, Path, Query, Response, UploadFile, status
from starlette.requests import HTTPConnection

from app.core.deps import CurrentUserDep, Db
from app.core.field_paths import FieldPathsRoute
from app.features.projects.schemas import (
    DraftKind,
    DraftPatchIn,
    ProfileEntryIn,
    ProjectOut,
    ProjectStatus,
    ProjectSummary,
    SessionStarted,
)
from app.features.projects.service.briefs import retry_brief
from app.features.projects.service.drafts import patch_draft
from app.features.projects.service.profile_entry import add_profile_entry
from app.features.projects.service.runtime import ProjectsRuntime
from app.features.projects.service.screenshots import screenshot_file
from app.features.projects.service.submit import submit_project
from app.features.projects.service.views import get_project, list_projects

router = APIRouter(prefix="/projects", tags=["projects"], route_class=FieldPathsRoute)

ProjectId = Annotated[str, Path(min_length=1, max_length=36)]
_NOT_FOUND: dict[int | str, dict[str, Any]] = {404: {"description": "`project_not_found`"}}
_SUBMIT_ERRORS: dict[int | str, dict[str, Any]] = {
    404: {"description": "`project_not_found`"},
    409: {
        "description": "`project_not_ready` (énoncé absent), `review_in_progress` "
        "(`details.session_id`) ou `project_validated`"
    },
    413: {"description": "`file_too_large` : une capture dépasse 5 Mo, ou le corps 26 Mo"},
    422: {"description": "`details.fields` : `repo_url`, `description`, `screenshots`"},
    503: {"description": "`review_unavailable` : le rendu n'est pas gardé"},
}
_ENTRY_ERRORS: dict[int | str, dict[str, Any]] = {
    404: {"description": "`project_not_found`"},
    409: {
        "description": "`project_not_validated`, `entry_already_added`, `profile_required`, "
        "`profile_draft_pending` ou `profile_projects_full`"
    },
}
_IMAGE_RESPONSE: dict[int | str, dict[str, Any]] = {
    200: {
        "content": {
            media: {"schema": {"type": "string", "format": "binary"}}
            for media in ("image/png", "image/jpeg", "image/webp")
        }
    },
    404: {"description": "`project_not_found` ou `screenshot_not_found`"},
}


def get_projects_runtime(conn: HTTPConnection) -> ProjectsRuntime:
    """Les projets ouverts par le lifespan (`app.state.daily.projects`)."""
    runtime: ProjectsRuntime = conn.app.state.daily.projects
    return runtime


ProjectsDep = Annotated[ProjectsRuntime, Depends(get_projects_runtime)]


@router.get("", response_model=list[ProjectSummary])
async def get_projects(
    current: CurrentUserDep, db: Db, rt: ProjectsDep, status: ProjectStatus | None = None
) -> list[ProjectSummary]:
    """Le Portfolio : programme, semaine et rang de chaque projet ; `status` filtre."""
    return await list_projects(rt, db, current.id, status)


@router.get("/{project_id}", response_model=ProjectOut, responses=_NOT_FOUND)
async def get_one_project(
    project_id: ProjectId, current: CurrentUserDep, db: Db, rt: ProjectsDep
) -> ProjectOut:
    return await get_project(rt, db, current.id, project_id)


@router.post(
    "/{project_id}/submit",
    response_model=SessionStarted,
    status_code=status.HTTP_202_ACCEPTED,
    responses=_SUBMIT_ERRORS,
)
async def post_submit(
    project_id: ProjectId,
    current: CurrentUserDep,
    rt: ProjectsDep,
    repo_url: Annotated[str | None, Form()] = None,
    description: Annotated[str | None, Form()] = None,
    screenshots: Annotated[list[UploadFile] | None, File()] = None,
) -> SessionStarted:
    """Rend le projet : un lien http(s) et/ou une description (4 000 caractères au plus), jusqu'à
    cinq captures PNG, JPEG ou WebP de 5 Mo (vérifiées par leurs octets, jamais par leur nom).
    Les captures ne sont pas envoyées au modèle : elles sont montrées dans le Portfolio."""
    return await submit_project(
        rt,
        current.id,
        project_id,
        repo_url=repo_url,
        description=description,
        files=screenshots or [],
    )


@router.get(
    "/{project_id}/screenshots/{number}",
    response_class=Response,
    responses=_IMAGE_RESPONSE,
)
async def get_screenshot(
    project_id: ProjectId,
    number: Annotated[int, Path(ge=1, le=5)],
    current: CurrentUserDep,
    rt: ProjectsDep,
    submission: Annotated[int, Query(ge=1, le=10)] = 1,
) -> Response:
    """La capture `number` (de 1 à 5) du rendu `submission` (1 : le dernier, 2 : celui d'avant…),
    dans son type d'origine, jamais mise en cache."""
    data, media_type = await screenshot_file(rt, current.id, project_id, number, submission)
    headers = {
        "Cache-Control": "no-store",
        "Content-Disposition": "inline",
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "sandbox",
    }
    return Response(content=data, media_type=media_type, headers=headers)


@router.patch("/{project_id}/drafts/{kind}", response_model=ProjectOut, responses=_NOT_FOUND)
async def patch_one_draft(
    project_id: ProjectId,
    kind: DraftKind,
    body: DraftPatchIn,
    current: CurrentUserDep,
    rt: ProjectsDep,
) -> ProjectOut:
    """Retouche un brouillon : `entry` pour `profile_entry`, `content` (3 000 caractères au plus)
    pour les autres. Un brouillon « à vérifier » modifié est recontrôlé."""
    return await patch_draft(rt, current.id, project_id, kind, body)


@router.post("/{project_id}/profile-entry", response_model=ProjectOut, responses=_ENTRY_ERRORS)
async def post_profile_entry(
    project_id: ProjectId, body: ProfileEntryIn, current: CurrentUserDep, rt: ProjectsDep
) -> ProjectOut:
    """Ajoute le projet validé au profil maître (nouvelle version validée) : le seul chemin."""
    return await add_profile_entry(rt, current.id, project_id, body)


@router.post(
    "/{project_id}/brief",
    response_model=SessionStarted,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        404: {"description": "`project_not_found`"},
        409: {"description": "`brief_not_failed`"},
        503: {"description": "`brief_unavailable`"},
    },
)
async def post_brief(
    project_id: ProjectId, current: CurrentUserDep, rt: ProjectsDep
) -> SessionStarted:
    """Relance l'énoncé d'un projet dont les trois essais ont échoué."""
    return await retry_brief(rt, current.id, project_id)
