"""Evaluator port, bound to the answer reserved by the engine."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.tools.recruitment_process_port import (
    RecruitmentContext,
    RecruitmentCriterion,
    RecruitmentGrade,
)
from app.core.errors import AppError
from app.db.base import utcnow
from app.db.models.recruitment_process import RecruitmentProcess
from app.features.recruitment_process.repository import RecruitmentCases
from app.features.recruitment_process.schemas import RecruitmentStep
from app.features.recruitment_process.service.steps import stored_steps


def _bound(
    row: RecruitmentProcess, session_id: str
) -> tuple[list[RecruitmentStep], RecruitmentStep]:
    steps = stored_steps(row)
    found = next((step for step in steps if step.session_id == session_id), None)
    if found is None:
        raise AppError(
            "recruitment_step_changed", "This step is no longer bound to the session.", 409
        )
    return steps, found


class AgentRecruitmentStore:
    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = factory

    async def context(self, user_id: str, process_id: str, session_id: str) -> RecruitmentContext:
        async with self._factory() as db:
            row = await RecruitmentCases(db, user_id).require(process_id)
            _, step = _bound(row, session_id)
            if step.answer is None:
                raise AppError("recruitment_answer_missing", "The step answer is missing.", 409)
            return RecruitmentContext(
                offer=str(row.offer["title"]),
                requirements=[str(item)[:600] for item in row.offer["requirements"][:10]],
                kind=step.kind,
                prompt=step.prompt,
                answer=step.answer,
                criteria=[RecruitmentCriterion.model_validate(item) for item in row.rubric],
                project=row.project if step.kind == "project" else None,
                graded=step.grade is not None,
            )

    async def grade(
        self, user_id: str, process_id: str, session_id: str, grade: RecruitmentGrade
    ) -> None:
        async with self._factory.begin() as db:
            await db.execute(text("BEGIN IMMEDIATE"))
            row = await RecruitmentCases(db, user_id).require(process_id)
            steps, step = _bound(row, session_id)
            if step.grade is None:
                step.grade = grade
                step.graded_at = utcnow()
                row.steps = [item.model_dump(mode="json") for item in steps]
