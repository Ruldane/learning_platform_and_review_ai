"""Questionnaire version and markers viewable during a retry."""

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.practice import PracticeSummary, compare_versions, content_version
from app.db.models.study import QuizAttempt, QuizQuestion
from app.features.quiz.repository import AttemptRepository, QuestionRepository
from app.features.quiz.service.quizzes import owned_quiz


def question_version(questions: Sequence[QuizQuestion]) -> str:
    """Keep stored version hashes stable across the multiple-choice code migration."""
    return content_version(
        [
            (
                q.id,
                q.rank,
                "qcm" if q.type == "mcq" else q.type,
                q.prompt,
                q.code,
                q.choices,
                q.correct_index,
                q.expected,
                q.rubric,
                q.skill,
            )
            for q in questions
        ]
    )


def _summary(attempt: QuizAttempt, current_version: str, total: int) -> PracticeSummary:
    results = attempt.results or []
    points: list[float] = []
    for item in results:
        point = item.get("points") if isinstance(item, dict) else None
        if isinstance(point, (int, float)) and not isinstance(point, bool) and 0 <= point <= 1:
            points.append(point)
    errors = sum(point < 1 for point in points) if points and len(points) == len(results) else None
    answers = [
        item
        for item in attempt.answers
        if isinstance(item, dict)
        and (item.get("choice") is not None or str(item.get("text") or "").strip())
    ]
    version = compare_versions(current_version, attempt.question_version)
    return PracticeSummary(
        id=attempt.id,
        created_at=attempt.created_at,
        version=version,
        elapsed_ms=attempt.elapsed_ms,
        errors=errors,
        progress=len(answers) if attempt.answers or version == "same" else None,
        total=total if version == "same" else len(results) or None,
        score_percent=attempt.score,
    )


async def read_history(
    db: AsyncSession, user_id: str, quiz_id: str, attempt_id: str | None = None
) -> list[PracticeSummary]:
    quiz = await owned_quiz(db, user_id, quiz_id)
    if quiz.status != "ready":
        return []
    questions = await QuestionRepository(db, user_id).for_quiz(quiz_id)
    version = question_version(questions)
    repo = AttemptRepository(db, user_id)
    attempts = await repo.recent_completed(quiz_id, version)
    if attempt_id and all(attempt.id != attempt_id for attempt in attempts):
        linked = await repo.get_fresh(attempt_id)
        if linked and linked.quiz_id == quiz_id and linked.status in ("graded", "failed"):
            attempts.append(linked)
    return [_summary(attempt, version, len(questions)) for attempt in attempts]
