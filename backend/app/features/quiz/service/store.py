"""Port des quiz (`QuizStore`, D100) sur la feature `quiz` : implémentation branchée par
`bootstrap.agent_ports` (D101). Chaque appel ouvre sa propre session de base, courte, et la
commite (D66) ; chaque appel vérifie que le quiz ou la tentative est à l'utilisateur (404).

Écritures idempotentes (SPEC 9.4) : `save_quiz` gardé par `UPDATE … WHERE status != 'ready'`
(rejoué : le nombre de questions, rien de plus) ; `quiz_failed` ne touche jamais un quiz prêt ;
`save_grades` gardé par `UPDATE … WHERE status = 'grading'`, sous le verrou du programme pris
AVANT la transaction (F4) ; le reflet des niveaux dans la mémoire vient après le commit, hors du
verrou, et se rattrape au rejeu. Journaux : identifiants et nombres seulement (SPEC 17.2)."""

import logging
from collections.abc import Mapping

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.quiz_port import (
    AttemptToGrade,
    GradedSaved,
    GradingItem,
    ModuleMaterial,
    QuizDraft,
)
from app.core.errors import AppError
from app.core.skills import normalize_skill_name
from app.db.models.program import Module
from app.db.models.study import Quiz
from app.features.lessons.service.lessons import ready_markdown
from app.features.memory.service.skill_levels import reflect_skill_levels
from app.features.program.service.programs import load
from app.features.quiz.repository import AttemptRepository, QuestionRepository, QuizRepository
from app.features.quiz.service.attempts import attempt_not_found
from app.features.quiz.service.cards import NewCard, add_cards
from app.features.quiz.service.grading import GradeContext, grade, module_skills, saved_of
from app.features.quiz.service.quizzes import lesson_not_ready, owned_quiz
from app.features.quiz.service.runtime import QuizRuntime
from app.features.quiz.service.scoring import qcm_points
from app.features.settings.service import SettingsService
from app.features.skills.service import SkillLevel, SkillsService

logger = logging.getLogger(__name__)

MAX_FAILURE = 300


async def _module(db: AsyncSession, user_id: str, quiz: Quiz) -> Module:
    loaded = await load(db, user_id, quiz.program_id)
    return next(m for m in loaded.modules if m.id == quiz.module_id)


def _skill(name: str, module: Module) -> str:
    """La compétence d'une question : celle du module de même nom normalisé, sinon la
    première du module (une compétence hors du module n'entre jamais au graphe)."""
    skills = [str(s) for s in module.skills]
    by_norm = {normalize_skill_name(s): s for s in skills}
    return by_norm.get(normalize_skill_name(name)) or (skills[0] if skills else name)


async def _context(db: AsyncSession, user_id: str, attempt_id: str) -> GradeContext:
    attempt = await AttemptRepository(db, user_id).get_fresh(attempt_id)
    if attempt is None:
        raise attempt_not_found()
    quiz = await owned_quiz(db, user_id, attempt.quiz_id)
    questions = await QuestionRepository(db, user_id).for_quiz(quiz.id)
    return GradeContext(attempt, quiz, await _module(db, user_id, quiz), questions)


class AgentQuizStore:
    def __init__(self, runtime: QuizRuntime) -> None:
        self._rt = runtime

    async def material(self, user_id: str, quiz_id: str) -> ModuleMaterial:
        async with self._rt.session_factory() as db:
            quiz = await owned_quiz(db, user_id, quiz_id)
            module = await _module(db, user_id, quiz)
            markdown = await ready_markdown(db, user_id, module.id)
            if markdown is None:
                raise lesson_not_ready()
            language = (await SettingsService(db, user_id).get()).lesson_language
            skills = [str(s) for s in module.skills]
            return ModuleMaterial(quiz.id, module.title, skills, markdown, language)

    async def _save_quiz(
        self, db: AsyncSession, user_id: str, session_id: str, quiz_id: str, draft: QuizDraft
    ) -> int:
        quiz = await owned_quiz(db, user_id, quiz_id)
        questions = QuestionRepository(db, user_id)
        if not await QuizRepository(db, user_id).mark_ready(quiz_id, session_id, draft.title):
            return len(await questions.for_quiz(quiz_id))
        module = await _module(db, user_id, quiz)
        for rank, q in enumerate(draft.questions, start=1):
            await questions.add(
                quiz_id=quiz_id,
                rank=rank,
                **q.model_dump(include={"type", "prompt", "code", "choices", "correct_index"}),
                expected=q.expected,
                rubric=list(q.rubric),
                explanation=q.explanation,
                skill=_skill(q.skill, module),
            )
        cards = [
            NewCard(c.front, c.back, _skill(c.skill or "", module), module.id, "lesson", quiz_id)
            for c in draft.flashcards
        ]
        await add_cards(db, user_id, cards, await self._rt.today(db, user_id))
        return len(draft.questions)

    async def save_quiz(self, user_id: str, session_id: str, quiz_id: str, draft: QuizDraft) -> int:
        async with self._rt.session_factory() as db:
            count = await self._save_quiz(db, user_id, session_id, quiz_id, draft)
            await db.commit()
        logger.info("Quiz rangé : session %s, quiz %s, %d question(s)", session_id, quiz_id, count)
        return count

    async def quiz_failed(self, user_id: str, quiz_id: str, reason: str) -> None:
        async with self._rt.session_factory() as db:
            await owned_quiz(db, user_id, quiz_id)
            await QuizRepository(db, user_id).mark_failed(quiz_id, reason.strip()[:MAX_FAILURE])
            await db.commit()
        logger.info("Quiz en échec : quiz %s", quiz_id)

    async def attempt(self, user_id: str, attempt_id: str) -> AttemptToGrade:
        async with self._rt.session_factory() as db:
            ctx = await _context(db, user_id, attempt_id)
            lesson = await ready_markdown(db, user_id, ctx.module.id) or ""
        answers = {a["question_id"]: a for a in ctx.attempt.answers if isinstance(a, dict)}
        items: list[GradingItem] = []
        points: dict[str, float] = {}
        for q in ctx.questions:
            answer = answers.get(q.id, {})
            if q.type == "qcm":
                points[f"q{q.rank}"] = qcm_points(q.correct_index, answer.get("choice"))
                continue
            items.append(
                GradingItem(
                    ref=f"q{q.rank}",
                    type=q.type,  # type: ignore[arg-type]  # colonne texte, valeurs de QuestionType
                    prompt=q.prompt,
                    code=q.code,
                    expected=q.expected,
                    rubric=[str(r) for r in q.rubric],
                    answer=str(answer.get("text", "")),
                )
            )
        return AttemptToGrade(attempt_id, ctx.module.title, items, points, lesson)

    async def _grade(
        self,
        user_id: str,
        session_id: str,
        attempt_id: str,
        grades: Mapping[str, tuple[float, str]],
    ) -> tuple[GradedSaved, list[tuple[str, SkillLevel]], str]:
        async with self._rt.session_factory() as db:
            repo = AttemptRepository(db, user_id)
            claimed = await repo.claim_graded(attempt_id)
            ctx = await _context(db, user_id, attempt_id)
            if claimed:
                today, now = await self._rt.today(db, user_id), self._rt.now()
                saved = await grade(db, self._rt.program, ctx, grades, now, today)
            elif ctx.attempt.status == "graded":
                saved = saved_of(ctx.attempt)
            else:
                raise AppError("attempt_not_grading", "Cette tentative n'est plus à noter.", 409)
            skills = module_skills(ctx) if saved.passed else []
            levels = await SkillsService(db, user_id).levels_of(skills)
            await db.commit()
        return saved, levels, ctx.module.title

    async def save_grades(
        self,
        user_id: str,
        session_id: str,
        attempt_id: str,
        grades: Mapping[str, tuple[float, str]],
    ) -> GradedSaved:
        async with self._rt.session_factory() as db:
            ctx = await _context(db, user_id, attempt_id)
        # F4 : le verrou du programme AVANT la transaction d'écriture (même ordre qu'`editing`).
        async with self._rt.program.program_lock(user_id, ctx.quiz.program_id):
            saved, levels, title = await self._grade(user_id, session_id, attempt_id, grades)
        if levels:
            try:
                await reflect_skill_levels(
                    self._rt.memory,
                    user_id,
                    levels,
                    author="examiner",
                    session_id=session_id,
                    reason=f"Quiz « {title} » réussi",
                )
            except Exception:
                logger.warning("Acquis non reflétés après un quiz : tentative %s", attempt_id)
        logger.info(
            "Tentative rangée : session %s, tentative %s, %d %%, %d fiche(s), %d tâche(s)",
            session_id,
            attempt_id,
            saved.score,
            saved.cards_created,
            saved.followup_tasks,
        )
        return saved
