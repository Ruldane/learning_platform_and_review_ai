"""Projections of completed gradings, without rereading answers in progress."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.practice import content_version
from app.db.models.daily import Project
from app.db.models.study import QuizAttempt
from app.features.error_atlas import repository
from app.features.error_atlas.schemas import AtlasEvidenceOut, AtlasReference
from app.features.projects.service.views import parse_moment

MAX_EVIDENCE = 60


def _snippet(value: object) -> str | None:
    return (value.strip()[:1200] or None) if isinstance(value, str) else None


def _quiz_evidence(attempt: QuizAttempt, title: str) -> list[AtlasEvidenceOut]:
    result = []
    for item in attempt.results or []:
        if not isinstance(item, dict):
            continue
        item_id, points = item.get("question_id"), item.get("points")
        if not isinstance(item_id, str) or not 1 <= len(item_id) <= 36:
            continue
        if isinstance(points, bool) or not isinstance(points, (int, float)) or not 0 <= points < 1:
            continue
        finding = _snippet(item.get("feedback")) or _snippet(item.get("explanation"))
        result.append(
            AtlasEvidenceOut(
                reference=AtlasReference(
                    kind="quiz", resource_id=attempt.quiz_id, source_id=attempt.id, item_id=item_id
                ),
                title=title,
                finding=finding or f"The grading awards {points:g} out of 1 to this question.",
                expected=_snippet(item.get("correct_answer")),
                recorded_at=attempt.graded_at or attempt.created_at,
            )
        )
    return result


def _project_evidence(project: Project) -> list[AtlasEvidenceOut]:
    evaluation = project.evaluation or {}
    at = parse_moment(evaluation.get("at"))
    results = evaluation.get("results")
    if at is None or evaluation.get("verdict") != project.status or not isinstance(results, list):
        return []
    criteria = (project.brief or {}).get("criteria")
    criteria = criteria if isinstance(criteria, list) else []
    revision = content_version(
        project.id, evaluation.get("session_id"), evaluation.get("at"), results, criteria
    )
    found = []
    for item in results:
        if not isinstance(item, dict) or item.get("met") is not False:
            continue
        index = item.get("index")
        if type(index) is not int or not 1 <= index <= len(criteria):
            continue
        expected = _snippet(criteria[index - 1])
        if expected is None:
            continue
        found.append(
            AtlasEvidenceOut(
                reference=AtlasReference(
                    kind="project", resource_id=project.id, source_id=revision, item_id=str(index)
                ),
                title=project.title,
                finding=_snippet(item.get("comment")) or "This criterion is marked as not met.",
                expected=expected,
                recorded_at=at,
            )
        )
    return found


async def list_evidence(db: AsyncSession, user_id: str) -> list[AtlasEvidenceOut]:
    quizzes = await repository.quiz_attempts(db, user_id)
    projects = await repository.project_evaluations(db, user_id)
    found = [evidence for row, title in quizzes for evidence in _quiz_evidence(row, title)]
    found.extend(evidence for row in projects for evidence in _project_evidence(row))
    found.sort(key=lambda item: item.recorded_at, reverse=True)
    return found[:MAX_EVIDENCE]


async def read_evidence(
    db: AsyncSession, user_id: str, reference: AtlasReference
) -> AtlasEvidenceOut:
    if reference.kind == "quiz":
        quizzes = await repository.quiz_attempts(
            db, user_id, reference.resource_id, reference.source_id
        )
        available = [evidence for row, title in quizzes for evidence in _quiz_evidence(row, title)]
    else:
        projects = await repository.project_evaluations(db, user_id, reference.resource_id)
        available = [evidence for row in projects for evidence in _project_evidence(row)]
    match = next((evidence for evidence in available if evidence.reference == reference), None)
    if match is None:
        raise AppError("atlas_evidence_not_found", "Grading or criterion not found.", 404)
    return match
