from hmac import compare_digest
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.features.project_handoffs.guide import preview_guide
from app.features.project_handoffs.repository import ProjectHandoffs
from app.features.project_handoffs.schemas import (
    ProjectHandoffApproval,
    ProjectHandoffDraft,
    ProjectHandoffOut,
    ProjectHandoffPreview,
    ProjectHandoffSource,
    ProjectHandoffSummary,
)
from app.features.projects.service.runtime import ProjectsRuntime
from app.features.projects.service.views import get_project


async def source(
    rt: ProjectsRuntime, db: AsyncSession, user_id: str, project_id: UUID
) -> ProjectHandoffSource:
    project = await get_project(rt, db, user_id, str(project_id))
    if not project.submissions:
        raise AppError("project_handoff_no_submission", "This project has no submission yet.", 409)
    submission = project.submissions[0]
    return ProjectHandoffSource(
        project_id=project_id,
        project_title=project.title,
        submitted_at=submission.at,
        description=submission.description,
        repo_url=submission.repo_url,
    )


async def preview(
    rt: ProjectsRuntime, db: AsyncSession, user_id: str, draft: ProjectHandoffDraft
) -> ProjectHandoffPreview:
    return preview_guide(await source(rt, db, user_id, draft.project_id), draft)


async def approve(
    rt: ProjectsRuntime, db: AsyncSession, user_id: str, body: ProjectHandoffApproval
) -> ProjectHandoffOut:
    selected = await source(rt, db, user_id, body.project_id)
    guide = preview_guide(selected, body)
    if not compare_digest(guide.digest, body.expected_digest):
        raise AppError("project_handoff_changed", "The guide has changed. Preview it again.", 409)
    row = await ProjectHandoffs(db, user_id).add(
        project_id=str(selected.project_id),
        project_title=selected.project_title,
        submitted_at=selected.submitted_at,
        digest=guide.digest,
        markdown=guide.markdown,
    )
    return ProjectHandoffOut.model_validate(row)


async def read(db: AsyncSession, user_id: str, handoff_id: UUID) -> ProjectHandoffOut:
    row = await ProjectHandoffs(db, user_id).get(str(handoff_id))
    if row is None:
        raise AppError("project_handoff_not_found", "Handoff guide not found.", 404)
    return ProjectHandoffOut.model_validate(row)


async def list_handoffs(db: AsyncSession, user_id: str) -> list[ProjectHandoffSummary]:
    rows = await ProjectHandoffs(db, user_id).history()
    return [ProjectHandoffSummary.model_validate(row) for row in rows]
