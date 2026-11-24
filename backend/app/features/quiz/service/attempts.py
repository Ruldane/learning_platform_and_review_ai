"""Quiz attempts (SPEC F9, D101): submitting the answers, then grading in a `quiz` session
(`grade` mode); reading an attempt with its grade, its corrections and its follow-up.

One attempt at a time per quiz: under the quiz lock, any `grading` attempt whose session is
terminal (failed, cancelled, or finished without grades) first moves to `failed`; a still-live
attempt gives 409 `attempt_in_progress`, and the partial unique index
`uq_quiz_attempts_grading` returns the same 409 if two submissions still get through (F3).
Answers are stored with the original index of the choices (the displayed order changes on a
retry, F27). A 422 never echoes the input: `details.fields` carries paths."""

import logging
from collections.abc import Sequence
from datetime import date
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.played import inherit_source
from app.db.models.study import QuizAttempt, QuizQuestion
from app.features.quiz.repository import AttemptRepository, QuestionRepository
from app.features.quiz.schemas import AnswerIn, AttemptCreate, AttemptOut, AttemptStarted
from app.features.quiz.service.ghost import question_version
from app.features.quiz.service.quizzes import graded_count, owned_quiz
from app.features.quiz.service.runtime import GRAPH, SUBJECT, QuizRuntime
from app.features.quiz.service.scoring import passed
from app.features.quiz.service.shuffle import choice_order
from app.features.quiz.service.status import (
    attempt_shown,
    interrupted,
    is_draft_reason,
    open_sessions,
    read_with_sessions,
)
from app.features.sessions.service import session_facts

logger = logging.getLogger(__name__)


def attempt_not_found() -> AppError:
    return AppError("attempt_not_found", "Attempt not found.", 404)


def quiz_incomplete() -> AppError:
    return AppError(
        "quiz_incomplete",
        "This quiz is not complete: it needs more questions before it can be answered.",
        409,
    )


def attempt_in_progress() -> AppError:
    return AppError("attempt_in_progress", "An attempt at this quiz is already being graded.", 409)


def _invalid(fields: list[str]) -> AppError:
    return AppError(
        "invalid_answers",
        "Invalid answers: unknown or duplicate question, or a choice outside the options.",
        422,
        {"fields": fields},
    )


def stored_answers(
    quiz_id: str, round_: int, questions: Sequence[QuizQuestion], answers: Sequence[AnswerIn]
) -> list[dict[str, Any]]:
    """Stored answers (choice mapped back to its original index); 422 `invalid_answers` if a
    question is unknown or duplicated, or a choice is outside the options (or on a question
    that is not an MCQ)."""
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
            count = len(question.choices) if question.type == "mcq" else 0
            if not 0 <= choice < count:
                fields.append(f"answers.{index}.choice")
                continue
            choice = choice_order(quiz_id, round_, question.id, count)[choice]
        out.append({"question_id": question.id, "choice": choice, "text": answer.text})
    if fields:
        raise _invalid(fields)
    return out


def retry_too_soon(attempts: Sequence[QuizAttempt], today: date) -> AppError | None:
    """409 `retry_too_soon` if the last graded attempt failed and its retry (local D+2) has
    not come yet."""
    graded = [a for a in attempts if a.status == "graded" and a.score is not None]
    if not graded or passed(graded[-1].score or 0):
        return None
    retry_on = graded[-1].retry_on
    if retry_on is None or today >= retry_on:
        return None
    return AppError(
        "retry_too_soon",
        f"Retry possible on {retry_on:%d/%m}.",
        409,
        {"retry_on": retry_on.isoformat()},
    )


async def _insert(
    db: AsyncSession, user_id: str, rt: QuizRuntime, quiz_id: str, body: AttemptCreate
) -> str:
    """Under the quiz lock: checks, interrupted attempts moved to failed, insertion
    (committed); returns the attempt id."""
    quiz = await owned_quiz(db, user_id, quiz_id)
    open_ids = await open_sessions(db, user_id, quiz_id)
    quiz = await owned_quiz(db, user_id, quiz_id)
    if quiz.status == "generating" and is_draft_reason(quiz.failure_reason):
        raise quiz_incomplete()
    if quiz.status != "ready":
        raise AppError("quiz_not_ready", "This quiz is not ready yet.", 409)
    repo = AttemptRepository(db, user_id)
    attempts = await repo.for_quizzes([quiz_id])
    questions = await QuestionRepository(db, user_id).for_quiz(quiz_id)
    answers = stored_answers(quiz_id, graded_count(attempts), questions, body.answers)
    if (too_soon := retry_too_soon(attempts, await rt.today(db, user_id))) is not None:
        raise too_soon
    grading = [a for a in attempts if a.status == "grading"]
    # Under the lock, an attempt with no stored session is no longer being launched.
    stale = [
        a.id
        for a in grading
        if a.session_id is None or interrupted(a.status, a.session_id, open_ids)
    ]
    if len(stale) < len(grading):
        raise attempt_in_progress()
    await repo.fail_grading(stale)
    try:
        attempt = await repo.add(
            quiz_id=quiz_id,
            answers=answers,
            status="grading",
            question_version=question_version(questions),
            elapsed_ms=body.elapsed_ms,
        )
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise attempt_in_progress() from None
    if stale:
        logger.info("Interrupted attempts: quiz %s, %d failed", quiz_id, len(stale))
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
    """Stores the attempt then starts its grading (202). See the module for errors."""
    async with rt.quiz_lock(user_id, quiz_id):
        async with rt.session_factory() as db:
            quiz = await owned_quiz(db, user_id, quiz_id)
            source = await session_facts(db, user_id, quiz.session_id) if quiz.session_id else None
            attempt_id = await _insert(db, user_id, rt, quiz_id, body)
        payload = {"mode": "grade", "attempt_id": attempt_id}
        try:
            with inherit_source(
                user_id,
                source.played_by if source else None,
                source.model_provider if source else None,
                has_origin=source is not None,
            ):
                sid = await rt.launcher.start(
                    user_id, GRAPH, payload, subject_type=SUBJECT, subject_id=quiz_id
                )
        except BaseException:
            await _set_session(rt, user_id, attempt_id, None)
            raise
        await _set_session(rt, user_id, attempt_id, sid)
    logger.info("Attempt submitted: quiz %s, attempt %s, session %s", quiz_id, attempt_id, sid)
    return AttemptStarted(attempt_id=attempt_id, session_id=sid)


async def get_attempt(db: AsyncSession, user_id: str, quiz_id: str, attempt_id: str) -> AttemptOut:
    """The attempt with its grade and corrections (only once graded)."""
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
