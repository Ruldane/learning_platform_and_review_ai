"""Tentatives d'un quiz (SPEC F9, D101) : envoi des réponses, puis notation dans une session
`quiz` (mode `grade`) ; lecture d'une tentative avec sa note, ses corrections et son suivi.

Une tentative à la fois par quiz : sous le verrou du quiz, toute tentative `grading` dont la
session est terminale (échouée, annulée, ou finie sans notes) passe d'abord à `failed` ; une
tentative encore vivante donne 409 `attempt_in_progress`, et l'index unique partiel
`uq_quiz_attempts_grading` rend la même 409 si deux envois passent quand même (F3).
Les réponses sont rangées avec l'indice d'origine des choix (l'ordre affiché change au nouvel
essai, F27). Une 422 ne recopie jamais la saisie : `details.fields` porte des chemins."""

import logging
from collections.abc import Sequence
from datetime import date
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models.study import QuizAttempt, QuizQuestion
from app.features.quiz.repository import AttemptRepository, QuestionRepository
from app.features.quiz.schemas import AnswerIn, AttemptCreate, AttemptOut, AttemptStarted
from app.features.quiz.service.quizzes import graded_count, owned_quiz
from app.features.quiz.service.runtime import GRAPH, SUBJECT, QuizRuntime
from app.features.quiz.service.scoring import passed
from app.features.quiz.service.shuffle import choice_order
from app.features.quiz.service.status import (
    attempt_shown,
    interrupted,
    open_sessions,
    read_with_sessions,
)

logger = logging.getLogger(__name__)


def attempt_not_found() -> AppError:
    return AppError("attempt_not_found", "Tentative introuvable.", 404)


def attempt_in_progress() -> AppError:
    return AppError(
        "attempt_in_progress", "Une tentative de ce quiz est déjà en cours de notation.", 409
    )


def _invalid(fields: list[str]) -> AppError:
    return AppError(
        "invalid_answers",
        "Réponses invalides : question inconnue, en double ou choix hors des propositions.",
        422,
        {"fields": fields},
    )


def stored_answers(
    quiz_id: str, round_: int, questions: Sequence[QuizQuestion], answers: Sequence[AnswerIn]
) -> list[dict[str, Any]]:
    """Réponses rangées (choix ramené à son indice d'origine) ; 422 `invalid_answers` si une
    question est inconnue ou en double, ou un choix hors des propositions (ou sur une question
    qui n'est pas un QCM)."""
    by_id = {q.id: q for q in questions}
    seen: set[str] = set()
    fields: list[str] = []
    out: list[dict[str, Any]] = []
    for index, answer in enumerate(answers):
        question = by_id.get(answer.question_id)
        if question is None or answer.question_id in seen:
            fields.append(f"answers.{index}.question_id")
            continue
        seen.add(answer.question_id)
        choice = answer.choice
        if choice is not None:
            count = len(question.choices) if question.type == "qcm" else 0
            if not 0 <= choice < count:
                fields.append(f"answers.{index}.choice")
                continue
            choice = choice_order(quiz_id, round_, question.id, count)[choice]
        out.append({"question_id": question.id, "choice": choice, "text": answer.text})
    if fields:
        raise _invalid(fields)
    return out


def retry_too_soon(attempts: Sequence[QuizAttempt], today: date) -> AppError | None:
    """409 `retry_too_soon` si la dernière tentative notée a échoué et que son nouvel essai
    (J+2 local) n'est pas encore venu."""
    graded = [a for a in attempts if a.status == "graded" and a.score is not None]
    if not graded or passed(graded[-1].score or 0):
        return None
    retry_on = graded[-1].retry_on
    if retry_on is None or today >= retry_on:
        return None
    return AppError(
        "retry_too_soon",
        f"Nouvel essai possible le {retry_on:%d/%m}.",
        409,
        {"retry_on": retry_on.isoformat()},
    )


async def _insert(
    db: AsyncSession, user_id: str, rt: QuizRuntime, quiz_id: str, body: AttemptCreate
) -> str:
    """Sous le verrou du quiz : contrôles, tentatives interrompues passées en échec, insertion
    (commitée) ; rend l'id de la tentative."""
    quiz = await owned_quiz(db, user_id, quiz_id)
    open_ids = await open_sessions(db, user_id, quiz_id)
    quiz = await owned_quiz(db, user_id, quiz_id)
    if quiz.status != "ready":
        raise AppError("quiz_not_ready", "Ce quiz n'est pas encore prêt.", 409)
    repo = AttemptRepository(db, user_id)
    attempts = await repo.for_quizzes([quiz_id])
    questions = await QuestionRepository(db, user_id).for_quiz(quiz_id)
    answers = stored_answers(quiz_id, graded_count(attempts), questions, body.answers)
    if (too_soon := retry_too_soon(attempts, await rt.today(db, user_id))) is not None:
        raise too_soon
    grading = [a for a in attempts if a.status == "grading"]
    # Sous le verrou, une tentative sans session rangée n'est plus en cours de lancement.
    stale = [
        a.id
        for a in grading
        if a.session_id is None or interrupted(a.status, a.session_id, open_ids)
    ]
    if len(stale) < len(grading):
        raise attempt_in_progress()
    await repo.fail_grading(stale)
    try:
        attempt = await repo.add(quiz_id=quiz_id, answers=answers, status="grading")
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise attempt_in_progress() from None
    if stale:
        logger.info("Tentatives interrompues : quiz %s, %d en échec", quiz_id, len(stale))
    return attempt.id


async def _set_session(rt: QuizRuntime, user_id: str, attempt_id: str, sid: str | None) -> None:
    async with rt.session_factory() as db:
        attempt = await AttemptRepository(db, user_id).get_fresh(attempt_id)
        if attempt is not None and sid is not None:
            attempt.session_id = sid
        elif attempt is not None:
            attempt.status = "failed"
        await db.commit()


async def create_attempt(
    rt: QuizRuntime, user_id: str, quiz_id: str, body: AttemptCreate
) -> AttemptStarted:
    """Range la tentative puis lance sa notation (202). Voir le module pour les erreurs."""
    async with rt.quiz_lock(user_id, quiz_id):
        async with rt.session_factory() as db:
            attempt_id = await _insert(db, user_id, rt, quiz_id, body)
        payload = {"mode": "grade", "attempt_id": attempt_id}
        try:
            sid = await rt.launcher.start(
                user_id, GRAPH, payload, subject_type=SUBJECT, subject_id=quiz_id
            )
        except BaseException:
            await _set_session(rt, user_id, attempt_id, None)
            raise
        await _set_session(rt, user_id, attempt_id, sid)
    logger.info("Tentative envoyée : quiz %s, tentative %s, session %s", quiz_id, attempt_id, sid)
    return AttemptStarted(attempt_id=attempt_id, session_id=sid)


async def get_attempt(db: AsyncSession, user_id: str, quiz_id: str, attempt_id: str) -> AttemptOut:
    """La tentative avec sa note et ses corrections (une fois notée seulement)."""
    await owned_quiz(db, user_id, quiz_id)

    async def read() -> QuizAttempt:
        found = await AttemptRepository(db, user_id).get_fresh(attempt_id)
        if found is None or found.quiz_id != quiz_id:
            raise attempt_not_found()
        return found

    attempt, open_ids = await read_with_sessions(
        db, user_id, quiz_id, read, lambda a: [(a.status, a.session_id)]
    )
    status = attempt_shown(attempt.status, attempt.session_id, open_ids)
    graded = status == "graded"
    return AttemptOut.model_validate(
        {
            "id": attempt.id,
            "status": status,
            "score": attempt.score if graded else None,
            "passed": passed(attempt.score or 0) if graded else None,
            "results": list(attempt.results or []) if graded else [],
            "followup": attempt.followup if graded else None,
        }
    )
