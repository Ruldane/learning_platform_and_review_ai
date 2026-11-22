from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.features.grade_appeals.repository import GradeAppeals
from app.features.grade_appeals.schemas import (
    GradeAppealCreate,
    GradeAppealCriterion,
    GradeAppealOut,
    GradeAppealProject,
    GradeAppealSource,
)
from app.features.grade_appeals.service.workflow import view
from app.features.projects.service.runtime import ProjectsRuntime
from app.features.projects.service.views import get_project, list_projects

_REVIEWED = {"validated", "to_redo"}


@dataclass(frozen=True)
class WrittenSubmission:
    project: GradeAppealProject
    text: str
    submitted_at: datetime
    criteria: list[GradeAppealCriterion]


async def projects(rt: ProjectsRuntime, db: AsyncSession, user_id: str) -> list[GradeAppealProject]:
    return [
        GradeAppealProject(id=row.id, title=row.title)
        for row in await list_projects(rt, db, user_id, None)
        if row.status in _REVIEWED
    ]


async def _written(
    rt: ProjectsRuntime, db: AsyncSession, user_id: str, project_id: str
) -> WrittenSubmission | None:
    row = await get_project(rt, db, user_id, project_id)
    if row.status not in _REVIEWED or row.evaluation is None or not row.submissions:
        return None
    last = row.submissions[0]
    if not last.description or not last.description.strip():
        return None
    return WrittenSubmission(
        project=GradeAppealProject(id=row.id, title=row.title),
        text=last.description,
        submitted_at=last.at,
        criteria=[
            GradeAppealCriterion(
                index=item.index,
                criterion=item.criterion,
                original_met=item.met,
                original_comment=item.comment,
            )
            for item in row.evaluation.results
            if item.criterion.strip()
        ],
    )


async def criteria(
    rt: ProjectsRuntime, db: AsyncSession, user_id: str, project_id: str
) -> list[GradeAppealCriterion]:
    found = await _written(rt, db, user_id, project_id)
    return found.criteria if found is not None else []


async def create(
    rt: ProjectsRuntime, db: AsyncSession, user_id: str, body: GradeAppealCreate
) -> GradeAppealOut:
    project_id = str(body.project_id)
    source = await _written(rt, db, user_id, project_id)
    if source is None:
        raise AppError(
            "grade_appeal_source_missing", "Choisis une remise écrite déjà évaluée.", 409
        )
    chosen = next((item for item in source.criteria if item.index == body.criterion_index), None)
    if chosen is None:
        raise AppError("grade_appeal_criterion_missing", "Ce critère est introuvable.", 404)
    frozen = GradeAppealSource(
        project=source.project,
        criterion=chosen,
        submission=source.text,
        submitted_at=source.submitted_at,
    )
    row = await GradeAppeals(db, user_id).add(
        project_id=project_id, source=frozen.model_dump(mode="json"), reason=body.reason
    )
    return await view(db, row)
