"""Quiz d'un module (SPEC F9, D101) : préparé à la demande (`POST /modules/{id}/quiz`, hors
14.2), liste par programme, détail sans aucune réponse attendue.

Lancement idempotent sous le verrou du module : quiz prêt → rendu tel quel (200) ; en
préparation → même session ; en échec (ou interrompu, lu d'après sa session) → relancé.
La ligne est commitée avant `launcher.start` : jamais le verrou d'écriture SQLite tenu pendant
le lancement (D66, D72). Journaux : identifiants seulement."""

import logging
from collections.abc import Sequence
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models.study import Quiz, QuizAttempt, QuizQuestion
from app.features.lessons.service.lessons import ready_markdown
from app.features.program.service.programs import load, program_of_module
from app.features.quiz.repository import AttemptRepository, QuestionRepository, QuizRepository
from app.features.quiz.schemas import (
    AttemptSummaryOut,
    QuestionOut,
    QuizOut,
    QuizStarted,
    QuizSummaryOut,
)
from app.features.quiz.service.runtime import GRAPH, SUBJECT, QuizRuntime
from app.features.quiz.service.scoring import passed
from app.features.quiz.service.shuffle import choice_order, question_order
from app.features.quiz.service.status import (
    attempt_shown,
    interrupted,
    open_sessions,
    open_sessions_by_quiz,
    quiz_shown,
    read_with_sessions,
)

logger = logging.getLogger(__name__)

LAUNCH_FAILED = "Le quiz n'a pas pu être lancé : réessaie dans un instant."


def quiz_not_found() -> AppError:
    return AppError("quiz_not_found", "Quiz introuvable.", 404)


def lesson_not_ready() -> AppError:
    return AppError(
        "lesson_not_ready", "La leçon de ce module n'est pas encore prête : le quiz attendra.", 409
    )


async def owned_quiz(db: AsyncSession, user_id: str, quiz_id: str) -> Quiz:
    quiz = await QuizRepository(db, user_id).get_fresh(quiz_id)
    if quiz is None:
        raise quiz_not_found()
    return quiz


async def _prepare(db: AsyncSession, user_id: str, module_id: str) -> QuizStarted | Quiz:
    """Sous le verrou : l'état à rendre tel quel, ou le quiz (créé ou remis à zéro) à lancer."""
    repo = QuizRepository(db, user_id)
    found = await repo.by_module(module_id)
    if found is not None:
        open_ids = await open_sessions(db, user_id, found.id)
        found = await repo.get_fresh(found.id)
        assert found is not None
        if found.status == "ready":
            return QuizStarted(quiz_id=found.id, session_id=found.session_id, status="ready")
        if found.status == "generating" and found.session_id in open_ids:
            return QuizStarted(quiz_id=found.id, session_id=found.session_id, status="generating")
    if await ready_markdown(db, user_id, module_id) is None:
        raise lesson_not_ready()
    if found is None:
        loaded = await load(db, user_id, await program_of_module(db, user_id, module_id))
        module = next(m for m in loaded.modules if m.id == module_id)
        return await repo.add(module_id=module_id, program_id=loaded.program.id, title=module.title)
    found.status, found.session_id, found.failure_reason = "generating", None, None
    return found


async def _set_session(rt: QuizRuntime, user_id: str, quiz_id: str, sid: str | None) -> None:
    async with rt.session_factory() as db:
        quiz = await QuizRepository(db, user_id).get_fresh(quiz_id)
        if quiz is not None and sid is not None:
            quiz.session_id = sid
        elif quiz is not None:
            quiz.status, quiz.failure_reason = "failed", LAUNCH_FAILED
        await db.commit()


async def start_quiz(rt: QuizRuntime, user_id: str, module_id: str) -> QuizStarted:
    """Prépare le quiz du module (voir le module). Module d'un autre : 404 `module_not_found` ;
    leçon pas prête : 409 `lesson_not_ready`."""
    async with rt.session_factory() as db:
        await program_of_module(db, user_id, module_id)
    async with rt.quiz_lock(user_id, module_id):
        async with rt.session_factory() as db:
            prepared = await _prepare(db, user_id, module_id)
            await db.commit()
        if isinstance(prepared, QuizStarted):
            return prepared
        quiz_id = prepared.id
        payload = {"mode": "generate", "quiz_id": quiz_id}
        try:
            sid = await rt.launcher.start(
                user_id, GRAPH, payload, subject_type=SUBJECT, subject_id=quiz_id
            )
        except BaseException:
            await _set_session(rt, user_id, quiz_id, None)
            raise
        await _set_session(rt, user_id, quiz_id, sid)
    logger.info("Quiz lancé : utilisateur %s, quiz %s, session %s", user_id, quiz_id, sid)
    return QuizStarted(quiz_id=quiz_id, session_id=sid, status="generating")


def _best(attempts: Sequence[QuizAttempt]) -> int | None:
    scores = [a.score for a in attempts if a.status == "graded" and a.score is not None]
    return max(scores) if scores else None


def retry_on_of(attempts: Sequence[QuizAttempt]) -> date | None:
    """Date du nouvel essai : celle de la dernière tentative notée, si elle est sous 80 % et
    qu'aucune n'a réussi ; sinon `None`."""
    graded = [a for a in attempts if a.status == "graded" and a.score is not None]
    if not graded or any(passed(a.score or 0) for a in graded):
        return None
    return graded[-1].retry_on


async def list_quizzes(db: AsyncSession, user_id: str, program_id: str) -> list[QuizSummaryOut]:
    """Un résumé par module non sauté du programme, dans l'ordre du programme."""
    loaded = await load(db, user_id, program_id)
    ranks = {week.id: week.rank for week in loaded.weeks}
    open_by_quiz = await open_sessions_by_quiz(db, user_id)  # D97 n° 9 : sessions, PUIS lignes
    quizzes = {q.module_id: q for q in await QuizRepository(db, user_id).for_program(program_id)}
    attempts = await AttemptRepository(db, user_id).for_quizzes([q.id for q in quizzes.values()])
    if any(
        interrupted(q.status, q.session_id, open_by_quiz.get(q.id, [])) for q in quizzes.values()
    ):  # lancé entre les deux lectures : relues, la session compte ouverte
        later = await open_sessions_by_quiz(db, user_id)
        for quiz_id, ids in later.items():
            known = open_by_quiz.setdefault(quiz_id, [])
            known += [sid for sid in ids if sid not in known]
    out: list[QuizSummaryOut] = []
    for module in (m for m in loaded.modules if not m.skipped):
        quiz = quizzes.get(module.id)
        status: str | None = None
        mine: list[QuizAttempt] = []
        if quiz is not None:
            status = quiz_shown(quiz.status, quiz.session_id, None, open_by_quiz.get(quiz.id, []))[
                0
            ]
            mine = [a for a in attempts if a.quiz_id == quiz.id]
        out.append(
            QuizSummaryOut.model_validate(
                {
                    "module_id": module.id,
                    "module_title": module.title,
                    "week_rank": ranks.get(module.week_id, 0),
                    "quiz_id": quiz.id if quiz is not None else None,
                    "status": status,
                    "best_score": _best(mine),
                    "retry_on": retry_on_of(mine),
                }
            )
        )
    return out


def graded_count(attempts: Sequence[QuizAttempt]) -> int:
    """Le numéro de l'essai suivant (F27) : le nombre de tentatives déjà notées."""
    return sum(1 for a in attempts if a.status == "graded")


def questions_out(
    quiz_id: str, round_: int, questions: Sequence[QuizQuestion]
) -> list[QuestionOut]:
    """Questions dans l'ordre de l'essai, choix mélangés ; jamais la réponse ni la grille."""
    by_id = {q.id: q for q in questions}
    order = question_order(quiz_id, round_, [q.id for q in questions])
    out: list[QuestionOut] = []
    for rank, qid in enumerate(order, start=1):
        q = by_id[qid]
        choices = [str(c) for c in q.choices]
        shown = [choices[i] for i in choice_order(quiz_id, round_, q.id, len(choices))]
        out.append(
            QuestionOut.model_validate(
                {"id": q.id, "rank": rank, "type": q.type, "prompt": q.prompt, "code": q.code}
                | {"choices": shown}
            )
        )
    return out


async def get_quiz(db: AsyncSession, user_id: str, quiz_id: str) -> QuizOut:
    await owned_quiz(db, user_id, quiz_id)

    async def read() -> tuple[Quiz, list[QuizAttempt]]:
        quiz = await owned_quiz(db, user_id, quiz_id)
        return quiz, await AttemptRepository(db, user_id).for_quizzes([quiz_id])

    (quiz, attempts), open_ids = await read_with_sessions(
        db,
        user_id,
        quiz_id,
        read,
        lambda r: [(r[0].status, r[0].session_id)] + [(a.status, a.session_id) for a in r[1]],
    )
    status, reason = quiz_shown(quiz.status, quiz.session_id, quiz.failure_reason, open_ids)
    questions = await QuestionRepository(db, user_id).for_quiz(quiz_id) if status == "ready" else []
    summaries = [
        AttemptSummaryOut.model_validate(
            {
                "id": a.id,
                "status": attempt_shown(a.status, a.session_id, open_ids),
                "score": a.score,
                "created_at": a.created_at,
            }
        )
        for a in attempts
    ]
    return QuizOut.model_validate(
        {
            "id": quiz.id,
            "module_id": quiz.module_id,
            "title": quiz.title,
            "status": status,
            "failure_reason": reason,
            "session_id": quiz.session_id,
            "questions": questions_out(quiz_id, graded_count(attempts), questions),
            "attempts": summaries,
        }
    )
