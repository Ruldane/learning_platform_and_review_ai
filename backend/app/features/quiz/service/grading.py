"""Grading an attempt (SPEC F9, D101), stored by the Examiner's port in ONE transaction,
under the program lock taken BEFORE it (F4), guarded by `UPDATE … SET status='graded' WHERE
status='grading'`: replayed, it re-reads the grade and writes nothing more.

≥ 80%: module skills to `validated` (`quiz` evidence, `ref_id` = the quiz, F21), card failures
reset to 0, reflection in memory after the commit. < 80%: targeted reviews ("Review:
{skill}", from tomorrow) and a new attempt ("Retake the quiz: {module}", at D+2) placed in the
budget, `retry_on` = local D+2. Always: cards from the mistakes, the module's "Retake the quiz"
tasks ticked (F18), the week's `quiz` task ticked when all its modules are graded, `quiz` log
line. Logs: ids and numbers only."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.quiz_port import GradedSaved
from app.core.skills import evidence
from app.db.models.program import Module
from app.db.models.study import Quiz, QuizAttempt, QuizQuestion
from app.features.capture.service.journal import JournalLinks, add_entry
from app.features.program.service.followup import (
    FollowupTask,
    add_followup,
    retry_title,
    tick_retry,
    tick_week_quiz,
)
from app.features.program.service.runtime import ProgramRuntime
from app.features.quiz.service.cards import NewCard, add_cards
from app.features.quiz.service.scoring import OPEN_SCORES, passed, qcm_points, score_percent
from app.features.quiz.service.scoring import weak_skills as weakest
from app.features.skills.service import SkillsService

RETRY_DAYS = 2
REVISION_MINUTES = 20
MISSING_FEEDBACK = "Answer not evaluated: re-read the correction."


@dataclass(frozen=True)
class GradeContext:
    """What the grade reads, under the lock: the attempt, its quiz, its module, its questions."""

    attempt: QuizAttempt
    quiz: Quiz
    module: Module
    questions: list[QuizQuestion]


def module_skills(ctx: GradeContext) -> list[str]:
    """The module's skills; failing that, those of the questions."""
    skills = [str(s) for s in ctx.module.skills] or [q.skill for q in ctx.questions]
    return list(dict.fromkeys(skills))


def _correct(question: QuizQuestion) -> str:
    if question.type == "mcq" and question.correct_index is not None:
        choices = [str(c) for c in question.choices]
        if 0 <= question.correct_index < len(choices):
            return choices[question.correct_index]
    return question.expected


def results_of(ctx: GradeContext, grades: Mapping[str, tuple[float, str]]) -> list[dict[str, Any]]:
    """One correction per question, in the original order. Multiple choice: point recomputed by
    the code; open: the Examiner's grade, brought back to 0 outside {0, 0.5, 1}."""
    answers = {a["question_id"]: a for a in ctx.attempt.answers if isinstance(a, dict)}
    out: list[dict[str, Any]] = []
    for q in ctx.questions:
        answer = answers.get(q.id, {})
        if q.type == "mcq":
            points, feedback = qcm_points(q.correct_index, answer.get("choice")), ""
        else:
            points, feedback = grades.get(f"q{q.rank}", (0.0, MISSING_FEEDBACK))
            points = float(points) if float(points) in OPEN_SCORES else 0.0
        out.append(
            {
                "question_id": q.id,
                "points": points,
                "correct_answer": _correct(q),
                "explanation": q.explanation,
                "feedback": feedback,
            }
        )
    return out


def error_cards(ctx: GradeContext, results: Sequence[Mapping[str, Any]]) -> list[NewCard]:
    """One card per missed question: front = statement (and code), back = expected answer and
    explanation."""
    cards: list[NewCard] = []
    for q, result in zip(ctx.questions, results, strict=True):
        if result["points"] >= 1:
            continue
        front = q.prompt if not q.code else f"{q.prompt}\n\n{q.code}"
        cards.append(
            NewCard(
                front=front,
                back=f"{result['correct_answer']}\n\n{q.explanation}".strip(),
                skill=q.skill,
                module_id=ctx.module.id,
                source="quiz",
                source_id=ctx.attempt.id,
            )
        )
    return cards


def followup_tasks(ctx: GradeContext, points: Sequence[float], today: date) -> list[FollowupTask]:
    """Reviews of the weak skills (3 at most) from tomorrow, then the new attempt at D+2."""
    weak = weakest([q.skill for q in ctx.questions], points)
    tasks = [
        FollowupTask(
            f"Review: {skill}",
            "read",
            REVISION_MINUTES,
            "Lesson re-read on this point and cards reviewed.",
            today + timedelta(days=1),
        )
        for skill in weak
    ]
    tasks.append(
        FollowupTask(
            retry_title(ctx.module.title),
            "quiz",
            REVISION_MINUTES,
            "Quiz retaken, 80% or more.",
            today + timedelta(days=RETRY_DAYS),
        )
    )
    return tasks


def journal_text(module: str, score: int, ok: bool, revisions: int, retry: date | None) -> str:
    if ok:
        return f'Quiz "{module}": {score}% — skills validated.'
    done = f"{revisions} review{'s' if revisions > 1 else ''} and " if revisions else ""
    when = f"a new attempt on {retry:%d/%m}." if retry else "a new attempt in 2 days."
    return f'Quiz "{module}": {score}% — {done}{when}'


async def _followup(
    db: AsyncSession, program: ProgramRuntime, ctx: GradeContext, points: list[float], today: date
) -> tuple[dict[str, Any], int]:
    """Reviews then new attempt placed in the budget; returns the follow-up and the number of
    tasks placed. The reviews have the same duration, type and first day: if one does not fit,
    neither do the following ones, so those placed are the first ones."""
    *revisions, retry = followup_tasks(ctx, points, today)
    user_id, module_id = ctx.attempt.user_id, ctx.module.id
    days, unplaced = await add_followup(db, program, user_id, module_id, revisions)
    retry_days, retry_unplaced = await add_followup(db, program, user_id, module_id, [retry])
    followup = {
        "revision_tasks": [t.title for t in revisions[: len(days)]],
        "retry_on": (today + timedelta(days=RETRY_DAYS)).isoformat(),
        "unplaced": unplaced + retry_unplaced,
    }
    return followup, len(days) + len(retry_days)


async def grade(
    db: AsyncSession,
    program: ProgramRuntime,
    ctx: GradeContext,
    grades: Mapping[str, tuple[float, str]],
    now: datetime,
    today: date,
) -> GradedSaved:
    """Stores the grade (the attempt has just been claimed `graded`); does not commit."""
    attempt, user_id = ctx.attempt, ctx.attempt.user_id
    results = results_of(ctx, grades)
    points = [float(r["points"]) for r in results]
    score = score_percent(points)
    ok = passed(score)
    cards = await add_cards(db, user_id, error_cards(ctx, results), today)
    await tick_retry(db, program, user_id, ctx.module.id)
    followup: dict[str, Any] = {"revision_tasks": [], "retry_on": None, "unplaced": 0}
    placed = 0
    if ok:
        skills = SkillsService(db, user_id)
        label = f'Quiz "{ctx.module.title}": {score}% ({today:%d/%m})'
        await skills.raise_levels(
            module_skills(ctx), "validated", evidence("quiz", ctx.quiz.id, label, now)
        )
        await skills.reset_fail_streaks(module_skills(ctx))
    else:
        followup, placed = await _followup(db, program, ctx, points, today)
    attempt.score, attempt.results, attempt.graded_at = score, results, now
    # Counts kept for a replay (the announcement re-reads the same thing); outside the contract.
    attempt.followup = followup | {"tasks_added": placed, "cards_created": cards}
    attempt.retry_on = None if ok else today + timedelta(days=RETRY_DAYS)
    await db.flush()
    await tick_week_quiz(db, program, user_id, ctx.module.id)
    revisions = len(followup["revision_tasks"])
    await add_entry(
        db,
        user_id,
        kind="quiz",
        text=journal_text(ctx.module.title, score, ok, revisions, attempt.retry_on),
        occurred_on=today,
        ref_key=f"quiz:{attempt.id}",
        links=JournalLinks(session_id=attempt.session_id, quiz_attempt_id=attempt.id),
        data={"quiz_id": ctx.quiz.id, "score": score, "passed": ok},
    )
    return GradedSaved(attempt.id, score, ok, cards, placed)


def saved_of(attempt: QuizAttempt) -> GradedSaved:
    """The grade already stored (replay): nothing is rewritten."""
    score = attempt.score or 0
    followup = attempt.followup or {}
    cards, placed = int(followup.get("cards_created", 0)), int(followup.get("tasks_added", 0))
    return GradedSaved(attempt.id, score, passed(score), cards, placed)
