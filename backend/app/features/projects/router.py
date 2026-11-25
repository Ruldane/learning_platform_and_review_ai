"""Proof mini projects API (SPEC 14.2, P1 to P3, P19, D166): Portfolio, project, submission (202,
the review runs in the background), screenshots, edited drafts, master profile entry and
new brief attempt. All on behalf of the current user (404 on another user's project);
a 422 names the fields, never copying the submission."""

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

from app.core.caller import ConfirmedGesture
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
    """Like `FieldPathsRoute`, and a submission text field over 1 MB (Starlette's limit,
    never a screenshot) is a 422 `fields: ["description"]`: the description is the only field
    that can reasonably reach it. A malformed body stays a 400."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        handler = super().get_route_handler()

        async def route(request: Request) -> Response:
            try:
                return await handler(request)
            except HTTPException as exc:
                # Starlette rejects a form field over 1 MB with a 400 ("Part exceeded
                # maximum size"): it is a Starlette `HTTPException`, not a FastAPI one.
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
        "description": "`project_not_ready` (no brief), `review_in_progress` "
        "(`details.session_id`) or `project_validated`"
    },
    413: {"description": "`file_too_large`: a screenshot exceeds 5 MB, or the body 26 MB"},
    422: {"description": "`details.fields` : `repo_url`, `description`, `screenshots`"},
    503: {"description": "`review_unavailable`: the submission is not kept"},
}
_ENTRY_ERRORS: dict[int | str, dict[str, Any]] = {
    404: {"description": "`project_not_found`"},
    409: {
        "description": "`project_not_validated`, `entry_already_added`, `profile_required`, "
        "`profile_draft_pending` or `profile_projects_full`"
    },
}
_IMAGE_RESPONSE: dict[int | str, dict[str, Any]] = {
    200: {
        "content": {
            media: {"schema": {"type": "string", "format": "binary"}}
            for media in ("image/png", "image/jpeg", "image/webp")
        }
    },
    404: {"description": "`project_not_found` or `screenshot_not_found`"},
}


def get_projects_runtime(conn: HTTPConnection) -> ProjectsRuntime:
    """The projects runtime opened by the lifespan (`app.state.daily.projects`)."""
    runtime: ProjectsRuntime = conn.app.state.daily.projects
    return runtime


ProjectsDep = Annotated[ProjectsRuntime, Depends(get_projects_runtime)]


@router.get("", response_model=list[ProjectSummary])
async def get_projects(
    current: CurrentUserDep, db: Db, rt: ProjectsDep, status: ProjectStatus | None = None
) -> list[ProjectSummary]:
    """The Portfolio: program, week and rank of each project; `status` filters."""
    return await list_projects(rt, db, current.id, status)


@router.post(
    "",
    response_model=ProjectOut,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "`module_not_found`"},
        409: {"description": "`project_exists` or `module_skipped`"},
    },
)
async def post_project(
    body: ProjectCreateIn, current: CurrentUserDep, rt: ProjectsDep
) -> ProjectOut:
    """Writes a module's mini project directly: the brief is January's or Claude's,
    with no agent and no model call; the project is "to do"."""
    return await create_project(rt, current.id, body)


@router.patch(
    "/{project_id}",
    response_model=ProjectOut,
    responses={
        404: {"description": "`project_not_found`"},
        409: {
            "description": "`project_not_editable`: the project is submitted, reviewed or validated"
        },
    },
)
async def patch_one_project(
    project_id: ProjectId, body: ProjectBriefPatch, current: CurrentUserDep, rt: ProjectsDep
) -> ProjectOut:
    """Edits the brief of a project without a submission, with no agent."""
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


@router.post("/{project_id}/github-claims", status_code=201, dependencies=[ConfirmedGesture])
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
    dependencies=[ConfirmedGesture],
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
    """Submits the project: an http(s) link and/or a description (4,000 characters at most), up to
    five PNG, JPEG or WebP screenshots of 5 MB (checked by their bytes, never by their name).
    Screenshots are not sent to the model: they are shown in the Portfolio."""
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
    """Screenshot `number` (1 to 5) of submission `submission` (1: the latest, 2: the one before…),
    in its original type, never cached."""
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
    """Edits a draft: `entry` for `profile_entry`, `content` (3,000 characters at most)
    for the others. An edited "to check" draft is checked again."""
    return await patch_draft(rt, current.id, project_id, kind, body)


@router.post("/{project_id}/profile-entry", response_model=ProjectOut, responses=_ENTRY_ERRORS)
async def post_profile_entry(
    project_id: ProjectId, body: ProfileEntryIn, current: CurrentUserDep, rt: ProjectsDep
) -> ProjectOut:
    """Adds the validated project to the master profile (new validated version): the only path."""
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
    """Restarts the brief of a project whose three attempts failed."""
    return await retry_brief(rt, current.id, project_id)


@router.post(
    "/{project_id}/drafts",
    response_model=SessionStarted,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        404: {"description": "`project_not_found`"},
        409: {
            "description": "`project_not_validated`, `drafts_present` (the project already has its "
            "drafts) or `review_in_progress` (`details.session_id`)"
        },
        503: {"description": "`drafts_unavailable`: the launch is refused, nothing changes"},
    },
)
async def post_drafts(
    project_id: ProjectId, current: CurrentUserDep, rt: ProjectsDep
) -> SessionStarted:
    """Restarts the drafts of a validated project that has none (writing them had failed,
    D173 no. 4): a session writes them without redoing the review."""
    return await regenerate_drafts(rt, current.id, project_id)
