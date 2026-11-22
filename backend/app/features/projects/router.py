"""API des mini projets preuves (SPEC 14.2, P1 à P3, P19, D166) : Portfolio, projet, rendu (202,
l'évaluation tourne en tâche de fond), captures, brouillons retouchés, entrée au profil maître et
nouvel essai de l'énoncé. Toutes au nom de l'utilisatrice courante (404 sur le projet d'une autre) ;
une 422 nomme les champs, sans jamais recopier le rendu."""

from collections.abc import Callable, Coroutine
from typing import Annotated, Any
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Path,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from starlette.exceptions import HTTPException
from starlette.requests import HTTPConnection

from app.core.caller import JanuaryOnly
from app.core.deps import CurrentUserDep, Db
from app.core.field_paths import FieldPathsRoute
from app.features.projects.github_schemas import GithubClaimIn, GithubClaimOut, GithubProofOut
from app.features.projects.schemas import (
    DraftKind,
    DraftPatchIn,
    ProfileEntryIn,
    ProjectBriefPatch,
    ProjectCreateIn,
    ProjectOut,
    ProjectStatus,
    ProjectSummary,
    SessionStarted,
)
from app.features.projects.service.briefs import retry_brief
from app.features.projects.service.direct import create_project, patch_project
from app.features.projects.service.drafts import patch_draft
from app.features.projects.service.errors import invalid_submission
from app.features.projects.service.github import issue_github_claim, list_github_proofs
from app.features.projects.service.profile_entry import add_profile_entry
from app.features.projects.service.regenerate import regenerate_drafts
from app.features.projects.service.runtime import ProjectsRuntime
from app.features.projects.service.screenshots import screenshot_file
from app.features.projects.service.submit import submit_project
from app.features.projects.service.views import get_project, list_projects


class FormRoute(FieldPathsRoute):
    """Comme `FieldPathsRoute`, et un champ texte du rendu de plus de 1 Mo (limite de Starlette,
    jamais une capture) est une 422 `fields: ["description"]` : la description est le seul champ
    qui peut raisonnablement l'atteindre. Un corps mal formé reste une 400."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        handler = super().get_route_handler()

        async def route(request: Request) -> Response:
            try:
                return await handler(request)
            except HTTPException as exc:
                # Starlette refuse un champ de formulaire de plus de 1 Mo par une 400 (« Part
                # exceeded maximum size ») : c'est une `HTTPException` de Starlette, pas de FastAPI.
                if exc.status_code == 400 and "maximum size" in str(exc.detail):
                    raise invalid_submission(["description"]) from None
                raise

        return route


router = APIRouter(prefix="/projects", tags=["projects"], route_class=FormRoute)

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


@router.post(
    "",
    response_model=ProjectOut,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "`module_not_found`"},
        409: {"description": "`project_exists` ou `module_skipped`"},
    },
)
async def post_project(
    body: ProjectCreateIn, current: CurrentUserDep, rt: ProjectsDep
) -> ProjectOut:
    """Écrit le mini projet d'un module en direct : l'énoncé est celui de January ou de Claude,
    sans agent ni appel au modèle ; le projet est « à faire »."""
    return await create_project(rt, current.id, body)


@router.patch(
    "/{project_id}",
    response_model=ProjectOut,
    responses={
        404: {"description": "`project_not_found`"},
        409: {"description": "`project_not_editable` : le projet est rendu, évalué ou validé"},
    },
)
async def patch_one_project(
    project_id: ProjectId, body: ProjectBriefPatch, current: CurrentUserDep, rt: ProjectsDep
) -> ProjectOut:
    """Retouche l'énoncé d'un projet sans rendu, sans agent."""
    return await patch_project(rt, current.id, project_id, body)


@router.get("/{project_id}", response_model=ProjectOut, responses=_NOT_FOUND)
async def get_one_project(
    project_id: ProjectId, current: CurrentUserDep, db: Db, rt: ProjectsDep
) -> ProjectOut:
    return await get_project(rt, db, current.id, project_id)


@router.get("/{project_id}/github-claims", responses=_NOT_FOUND)
async def get_github_proofs(
    project_id: ProjectId, current: CurrentUserDep, db: Db
) -> list[GithubProofOut]:
    return await list_github_proofs(db, current.id, project_id)


@router.post("/{project_id}/github-claims", status_code=201, dependencies=[JanuaryOnly])
async def make_github_claim(
    project_id: ProjectId,
    body: GithubClaimIn,
    current: CurrentUserDep,
    rt: ProjectsDep,
    response: Response,
) -> GithubClaimOut:
    response.headers["Cache-Control"] = "no-store"
    return await issue_github_claim(rt, current.id, project_id, body)


@router.post(
    "/{project_id}/submit",
    response_model=SessionStarted,
    status_code=status.HTTP_202_ACCEPTED,
    responses=_SUBMIT_ERRORS,
    dependencies=[JanuaryOnly],  # geste de January : jamais fait à sa place par le MCP
)
async def post_submit(
    project_id: ProjectId,
    current: CurrentUserDep,
    rt: ProjectsDep,
    repo_url: Annotated[str | None, Form()] = None,
    description: Annotated[str | None, Form()] = None,
    screenshots: Annotated[list[UploadFile] | None, File()] = None,
    github_claim_id: Annotated[UUID | None, Form()] = None,
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
        github_claim_id=github_claim_id,
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


@router.post(
    "/{project_id}/drafts",
    response_model=SessionStarted,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        404: {"description": "`project_not_found`"},
        409: {
            "description": "`project_not_validated`, `drafts_present` (le projet a déjà ses "
            "brouillons) ou `review_in_progress` (`details.session_id`)"
        },
        503: {"description": "`drafts_unavailable` : le lancement est refusé, rien n'est changé"},
    },
)
async def post_drafts(
    project_id: ProjectId, current: CurrentUserDep, rt: ProjectsDep
) -> SessionStarted:
    """Relance les brouillons d'un projet validé qui n'en a pas (leur écriture avait échoué,
    D173 n° 4) : une session les écrit sans refaire l'évaluation."""
    return await regenerate_drafts(rt, current.id, project_id)
