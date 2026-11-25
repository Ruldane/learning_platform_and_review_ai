"""A mini project brief written directly (phase 10, 10.W): January or Claude (through MCP)
provides the brief, the application stores it as the Practitioner's port does (`save_brief`), with
no agent and no session: the project becomes "to do" and takes the brief's title. The submission
and its review stay the application's (they launch an agent: not written here).

One project per module (unique index); the brief can only be edited while nothing is submitted."""

import logging

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.features.program.service.programs import load, program_of_module
from app.features.projects.repository import ProjectRepository
from app.features.projects.schemas import (
    ProjectBriefIn,
    ProjectBriefPatch,
    ProjectCreateIn,
    ProjectOut,
)
from app.features.projects.service.errors import (
    invalid_submission,
    module_skipped,
    project_exists,
    project_not_editable,
)
from app.features.projects.service.inputs import owned
from app.features.projects.service.runtime import ProjectsRuntime
from app.features.projects.service.views import project_out_live

logger = logging.getLogger(__name__)

EDITABLE = ("brief_pending", "brief_failed", "todo")  # no submission: the brief can still change


async def create_project(rt: ProjectsRuntime, user_id: str, body: ProjectCreateIn) -> ProjectOut:
    """The module's project, to do, with the given brief; 404 `module_not_found`, 409
    `project_exists` or `module_skipped`."""
    async with rt.session_factory() as db:
        program_id = await program_of_module(db, user_id, body.module_id)
    async with rt.ensure_lock(user_id), rt.session_factory() as db:
        loaded = await load(db, user_id, program_id)
        module = next(m for m in loaded.modules if m.id == body.module_id)
        if module.skipped:
            raise module_skipped()
        repo = ProjectRepository(db, user_id)
        if body.module_id in await repo.module_ids():
            raise project_exists()
        try:
            project = await repo.add(
                module_id=body.module_id,
                program_id=program_id,
                title=body.brief.title,
                brief=body.brief.model_dump(mode="json"),
                status="todo",
                brief_attempts=0,
                submissions=[],
                drafts={},
            )
            await db.commit()
        except IntegrityError:  # another request just created it
            await db.rollback()
            raise project_exists() from None
        project_id = project.id
    logger.info("Project written directly: module %s, project %s", body.module_id, project_id)
    async with rt.session_factory() as db:
        return await project_out_live(db, user_id, (await owned(db, user_id, project_id)))


def _merged(current: dict[str, object] | None, patch: ProjectBriefPatch) -> ProjectBriefIn:
    """The edited brief, fully revalidated; 422 `fields` if a field is missing (project without
    a brief) or out of bounds."""
    given = patch.model_dump(exclude_none=True)
    try:
        return ProjectBriefIn.model_validate({**(current or {}), **given})
    except ValidationError as exc:
        fields = sorted({str(error["loc"][0]) for error in exc.errors() if error["loc"]})
        raise invalid_submission(fields) from None


async def patch_project(
    rt: ProjectsRuntime, user_id: str, project_id: str, patch: ProjectBriefPatch
) -> ProjectOut:
    """Edits the brief of a project without a submission (409 `project_not_editable` otherwise); a
    project whose brief is not written receives it in full."""
    async with rt.project_lock(user_id, project_id), rt.session_factory() as db:
        row = await owned(db, user_id, project_id)
        if row.status not in EDITABLE:
            raise project_not_editable()
        brief = _merged(row.brief, patch)
        row.brief = brief.model_dump(mode="json")
        row.title = brief.title[:200]
        row.status, row.session_id = "todo", None
        await db.commit()
    logger.info("Brief edited directly: project %s", project_id)
    async with rt.session_factory() as db:
        return await project_out_live(db, user_id, (await owned(db, user_id, project_id)))
