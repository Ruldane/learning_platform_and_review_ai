"""Le quiz d'un module écrit en direct (phase 10, 10.W) : January ou Claude (par le MCP) fournit les
questions, l'application les range comme le fait le port de l'Examinateur (`save_quiz`), sans agent,
sans session et sans appel au modèle. Le quiz est prêt dès son écriture.

Un quiz par module (index unique). Tant qu'une tentative existe, ses questions ne bougent plus (les
réponses et les notes s'y réfèrent). Sous le verrou du module, comme le lancement d'un quiz."""

import logging
from typing import Any

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.quiz_port import MAX_QUESTIONS
from app.core.errors import AppError
from app.core.skills import normalize_skill_name
from app.db.models.program import Module
from app.db.models.study import Quiz, QuizQuestion
from app.features.program.service.programs import load, program_of_module
from app.features.quiz.repository import AttemptRepository, QuestionRepository, QuizRepository
from app.features.quiz.schemas import (
    QuestionIn,
    QuestionPatch,
    QuizOut,
    QuizPatch,
    QuizWriteIn,
)
from app.features.quiz.service.completeness import quiz_complete
from app.features.quiz.service.quizzes import get_quiz, owned_quiz
from app.features.quiz.service.runtime import QuizRuntime
from app.features.quiz.service.status import DRAFT_REASON, open_sessions

logger = logging.getLogger(__name__)


def quiz_exists() -> AppError:
    return AppError(
        "quiz_exists", "Ce module a déjà son quiz : ajoute ou retouche ses questions.", 409
    )


def quiz_generating() -> AppError:
    return AppError(
        "quiz_generating", "Une session écrit déjà le quiz de ce module : attends sa fin.", 409
    )


def quiz_has_attempts() -> AppError:
    return AppError(
        "quiz_has_attempts",
        "Ce quiz a déjà des tentatives : ses questions ne changent plus.",
        409,
    )


def quiz_full() -> AppError:
    return AppError("quiz_full", f"Un quiz compte {MAX_QUESTIONS} questions au plus.", 409)


def question_not_found() -> AppError:
    return AppError("question_not_found", "Question introuvable.", 404)


def module_skipped() -> AppError:
    return AppError("module_skipped", "Ce module est sauté : il n'a pas de quiz.", 409)


def _skill(name: str, module: Module) -> str:
    """La compétence d'une question : celle du module de même nom normalisé, sinon la première du
    module (une compétence hors du module n'entre jamais au graphe)."""
    skills = [str(s) for s in module.skills]
    by_norm = {normalize_skill_name(s): s for s in skills}
    return by_norm.get(normalize_skill_name(name)) or (skills[0] if skills else name)


def _row(question: QuestionIn, module: Module) -> dict[str, Any]:
    return {
        "type": question.type,
        "prompt": question.prompt.strip(),
        "code": question.code,
        "choices": list(question.choices),
        "correct_index": question.correct_index,
        "expected": question.expected.strip(),
        "rubric": list(question.rubric),
        "explanation": question.explanation.strip(),
        "skill": _skill(question.skill, module),
    }


async def _module(db: AsyncSession, user_id: str, program_id: str, module_id: str) -> Module:
    loaded = await load(db, user_id, program_id)
    return next(m for m in loaded.modules if m.id == module_id)


async def _busy(db: AsyncSession, user_id: str, quiz: Quiz) -> bool:
    """Un agent écrit le quiz : sa session est encore ouverte (sous le verrou du module, un quiz
    `generating` sans session n'est plus en cours de lancement)."""
    if quiz.status != "generating" or quiz.session_id is None:
        return False
    return quiz.session_id in await open_sessions(db, user_id, quiz.id)


async def create_quiz(rt: QuizRuntime, user_id: str, body: QuizWriteIn) -> QuizOut:
    """Voir le module : crée le quiz du module, ou remplit celui que la préparation avait laissé en
    échec ; 404 `module_not_found`, 409 `quiz_exists`, `quiz_generating` ou `module_skipped`."""
    async with rt.session_factory() as db:
        program_id = await program_of_module(db, user_id, body.module_id)
    async with rt.quiz_lock(user_id, body.module_id), rt.session_factory() as db:
        module = await _module(db, user_id, program_id, body.module_id)
        if module.skipped:
            raise module_skipped()
        repo = QuizRepository(db, user_id)
        quiz = await repo.by_module(body.module_id)
        if quiz is not None:
            if quiz.status == "ready" or quiz.failure_reason == DRAFT_REASON:
                raise quiz_exists()
            if await _busy(db, user_id, quiz):
                raise quiz_generating()
        if quiz is None:
            quiz = await repo.add(module_id=body.module_id, program_id=program_id, title=body.title)
        quiz.title, quiz.session_id = body.title, None
        questions = QuestionRepository(db, user_id)
        for rank, question in enumerate(body.questions, start=1):
            await questions.add(quiz_id=quiz.id, rank=rank, **_row(question, module))
        _settle(quiz, await questions.for_quiz(quiz.id))
        await db.commit()
        quiz_id = quiz.id
    logger.info("Quiz écrit en direct : module %s, quiz %s", body.module_id, quiz_id)
    async with rt.session_factory() as db:
        return await get_quiz(db, user_id, quiz_id)


def _settle(quiz: Quiz, questions: list[QuizQuestion]) -> None:
    """Prêt aux bornes de l'Examinateur, sinon « en préparation » (voir `completeness`)."""
    if quiz_complete(questions):
        quiz.status, quiz.failure_reason = "ready", None
    else:
        quiz.status, quiz.failure_reason = "generating", DRAFT_REASON


async def _editable(db: AsyncSession, user_id: str, quiz_id: str) -> Quiz:
    """Le quiz de l'utilisatrice dont les questions peuvent changer : prêt et sans tentative."""
    quiz = await owned_quiz(db, user_id, quiz_id)
    if quiz.status != "ready" and quiz.failure_reason != DRAFT_REASON:
        raise AppError("quiz_not_ready", "Ce quiz n'est pas prêt : écris-le d'abord.", 409)
    if await AttemptRepository(db, user_id).for_quizzes([quiz_id]):
        raise quiz_has_attempts()
    return quiz


async def add_question(rt: QuizRuntime, user_id: str, quiz_id: str, body: QuestionIn) -> QuizOut:
    """Une question de plus à la fin d'un quiz prêt sans tentative (409 `quiz_full` à 12)."""
    async with rt.session_factory() as db:
        module_id = (await owned_quiz(db, user_id, quiz_id)).module_id
    async with rt.quiz_lock(user_id, module_id), rt.session_factory() as db:
        quiz = await _editable(db, user_id, quiz_id)
        questions = QuestionRepository(db, user_id)
        existing = await questions.for_quiz(quiz_id)
        if len(existing) >= MAX_QUESTIONS:
            raise quiz_full()
        module = await _module(db, user_id, quiz.program_id, quiz.module_id)
        await questions.add(
            quiz_id=quiz_id,
            rank=max((q.rank for q in existing), default=0) + 1,
            **_row(body, module),
        )
        _settle(quiz, await questions.for_quiz(quiz_id))
        await db.commit()
    logger.info("Question ajoutée en direct : quiz %s", quiz_id)
    async with rt.session_factory() as db:
        return await get_quiz(db, user_id, quiz_id)


def _merged(question: QuizQuestion, patch: QuestionPatch) -> QuestionIn:
    """La question retouchée, revalidée en entier ; 422 `fields` sinon (jamais la valeur)."""
    current = {
        "type": question.type,
        "prompt": question.prompt,
        "code": question.code,
        "choices": [str(c) for c in question.choices],
        "correct_index": question.correct_index,
        "expected": question.expected,
        "rubric": [str(r) for r in question.rubric],
        "explanation": question.explanation,
        "skill": question.skill,
    }
    try:
        return QuestionIn.model_validate({**current, **patch.model_dump(exclude_none=True)})
    except ValidationError:
        fields = sorted(patch.model_dump(exclude_none=True)) or ["body"]
        raise AppError(
            "validation_error",
            "Requête invalide : vérifie les champs signalés.",
            422,
            {"fields": fields},
        ) from None


async def patch_question(
    rt: QuizRuntime, user_id: str, quiz_id: str, question_id: str, patch: QuestionPatch
) -> QuizOut:
    """Retouche une question d'un quiz prêt sans tentative (404 `question_not_found`)."""
    async with rt.session_factory() as db:
        module_id = (await owned_quiz(db, user_id, quiz_id)).module_id
    async with rt.quiz_lock(user_id, module_id), rt.session_factory() as db:
        quiz = await _editable(db, user_id, quiz_id)
        found = await QuestionRepository(db, user_id).get(question_id)
        if found is None or found.quiz_id != quiz_id:
            raise question_not_found()
        module = await _module(db, user_id, quiz.program_id, quiz.module_id)
        for name, value in _row(_merged(found, patch), module).items():
            setattr(found, name, value)
        await db.flush()
        _settle(quiz, await QuestionRepository(db, user_id).for_quiz(quiz_id))
        await db.commit()
    logger.info("Question retouchée en direct : quiz %s, question %s", quiz_id, question_id)
    async with rt.session_factory() as db:
        return await get_quiz(db, user_id, quiz_id)


async def patch_quiz(rt: QuizRuntime, user_id: str, quiz_id: str, patch: QuizPatch) -> QuizOut:
    """Change le titre d'un quiz prêt."""
    async with rt.session_factory() as db:
        quiz = await owned_quiz(db, user_id, quiz_id)
        if quiz.status != "ready" and quiz.failure_reason != DRAFT_REASON:
            raise AppError("quiz_not_ready", "Ce quiz n'est pas prêt : écris-le d'abord.", 409)
        quiz.title = patch.title
        await db.commit()
    async with rt.session_factory() as db:
        return await get_quiz(db, user_id, quiz_id)
