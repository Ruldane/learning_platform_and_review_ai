"""Port of the study sessions (`StudyStore`, D102) on the `study` feature: implementation wired by
`bootstrap.agent_ports` (D103). Each call opens its own short database session and checks that
the study session is the user's (404 otherwise).

`context` splits the ready lesson (`lesson_parts`); an exercise without a solution is omitted
(m4 of the 5.5 review: never an empty "Show the solution"). `finish` is the idempotent write of
`finish.py` (F4: program lock before the transaction)."""

from typing import cast

from app.agents.runtime.speech import CitationEntry
from app.agents.tools.study_port import (
    LessonSection,
    StudyContext,
    StudyFinished,
    StudyOutcome,
)
from app.core.errors import AppError
from app.db.models.study import StudyMode
from app.features.lessons.service.sections import lesson_parts, lesson_sources
from app.features.study.repository import StudyReadRepository, StudyRepository
from app.features.study.service.finish import finish_study, study_not_found
from app.features.study.service.runtime import StudyRuntime


def lesson_not_ready() -> AppError:
    return AppError("lesson_not_ready", "The lesson for this module isn't ready yet.", 409)


class AgentStudyStore:
    def __init__(self, runtime: StudyRuntime) -> None:
        self._rt = runtime

    async def context(self, user_id: str, study_session_id: str) -> StudyContext:
        async with self._rt.session_factory() as db:
            row = await StudyRepository(db, user_id).get_fresh(study_session_id)
            if row is None or row.kind != "guided":
                raise study_not_found()
            reads = StudyReadRepository(db, user_id)
            lesson = await reads.lesson(row.lesson_id)
            if lesson is None or lesson.status != "ready":
                raise lesson_not_ready()
            module = await reads.module(row.module_id)
            mode, question, markdown = row.mode, row.question, lesson.markdown
            module_title = module.title if module is not None else lesson.title
        parts = lesson_parts(markdown)
        solution = parts.solution.strip()
        return StudyContext(
            study_session_id=study_session_id,
            module_title=module_title,
            mode=cast(StudyMode, mode),
            objectives=parts.objectives,
            sections=[LessonSection(title, body) for title, body in parts.sections],
            exercise=parts.exercise.strip() if solution else "",
            solution=solution if parts.exercise.strip() else "",
            sources=[CitationEntry(n, title, url) for n, title, url in lesson_sources(markdown)],
            question=question,
        )

    async def finish(
        self, user_id: str, session_id: str, study_session_id: str, outcome: StudyOutcome
    ) -> StudyFinished:
        return await finish_study(self._rt, user_id, session_id, study_session_id, outcome)
