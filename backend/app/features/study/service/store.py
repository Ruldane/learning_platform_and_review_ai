"""Port des sessions d'étude (`StudyStore`, D102) sur la feature `study` : implémentation branchée
par `bootstrap.agent_ports` (D103). Chaque appel ouvre sa propre session de base, courte, et
vérifie que la session d'étude est à l'utilisatrice (404 sinon).

`context` découpe la leçon prête (`lesson_parts`) ; un exercice sans corrigé est omis (m4 de la
relecture de 5.5 : jamais de « Voir la solution » vide). `finish` est l'écriture idempotente de
`finish.py` (F4 : verrou du programme avant la transaction)."""

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
    return AppError("lesson_not_ready", "La leçon de ce module n'est pas encore prête.", 409)


class AgentStudyStore:
    def __init__(self, runtime: StudyRuntime) -> None:
        self._rt = runtime

    async def context(self, user_id: str, study_session_id: str) -> StudyContext:
        async with self._rt.session_factory() as db:
            row = await StudyRepository(db, user_id).get_fresh(study_session_id)
            if row is None:
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
