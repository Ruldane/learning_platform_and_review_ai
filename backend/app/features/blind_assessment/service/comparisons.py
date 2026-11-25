"""Freeze both CVs, reserve the evaluation and reveal the sources with the result."""

from dataclasses import asdict
from secrets import randbelow
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runtime.launcher import SessionLauncher
from app.agents.tools.blind_assessment_port import BLIND_GRAPH, BlindGrade
from app.core.errors import AppError
from app.db.models.agents import OPEN_SESSION_STATES
from app.db.models.blind_assessment import BlindAssessment
from app.features.blind_assessment.repository import BlindAssessments
from app.features.blind_assessment.schemas import (
    BlindCreate,
    BlindOptions,
    BlindOut,
    BlindResultOut,
    BlindRubric,
    BlindSourceLink,
    BlindStarted,
)
from app.features.blind_assessment.service.rubrics import RUBRICS
from app.features.blind_assessment.service.sources import choices, source_pair
from app.features.cv.service.runtime import CvRuntime
from app.features.sessions.service import session_facts


async def options(rt: CvRuntime, user_id: str) -> BlindOptions:
    return BlindOptions(sources=await choices(rt, user_id), rubrics=list(RUBRICS.values()))


async def create(db: AsyncSession, user_id: str, body: BlindCreate) -> BlindOut:
    a, b = await source_pair(db, user_id, str(body.first_version_id), str(body.second_version_id))
    if randbelow(2):
        a, b = b, a
    row = await BlindAssessments(db, user_id).add(
        rubric=RUBRICS[body.rubric].model_dump(),
        source_a=asdict(a),
        source_b=asdict(b),
    )
    return await _view(db, row)


async def _stage(
    db: AsyncSession, row: BlindAssessment
) -> Literal["draft", "evaluating", "failed", "complete"]:
    if row.stage != "evaluating":
        return row.stage
    found = await session_facts(db, row.user_id, row.session_id) if row.session_id else None
    return "evaluating" if found is not None and found.status in OPEN_SESSION_STATES else "failed"


def _link(source: dict[str, object]) -> BlindSourceLink:
    version_id = str(source["id"])
    return BlindSourceLink(
        id=version_id,
        label=str(source["label"]),
        url=f"/api/v1/cv/versions/{version_id}/pdf",
    )


def _result(row: BlindAssessment) -> BlindResultOut | None:
    if row.stage != "complete" or row.grade is None or row.evaluated_at is None:
        return None
    grade = BlindGrade.model_validate(row.grade)
    a, b = sum(grade.scores_a), sum(grade.scores_b)
    verdict: Literal["a", "b", "tie"] = "a" if a > b else "b" if b > a else "tie"
    return BlindResultOut(
        scores_a=grade.scores_a,
        scores_b=grade.scores_b,
        feedback=grade.feedback,
        source_a=_link(row.source_a),
        source_b=_link(row.source_b),
        evaluated_at=row.evaluated_at,
        verdict=verdict,
    )


async def _view(db: AsyncSession, row: BlindAssessment) -> BlindOut:
    return BlindOut(
        id=row.id,
        created_at=row.created_at,
        rubric=BlindRubric.model_validate(row.rubric),
        stage=await _stage(db, row),
        result=_result(row),
    )


async def read(db: AsyncSession, user_id: str, assessment_id: str) -> BlindOut:
    return await _view(db, await BlindAssessments(db, user_id).require(assessment_id))


async def history(db: AsyncSession, user_id: str) -> list[BlindOut]:
    return [await _view(db, row) for row in await BlindAssessments(db, user_id).recent()]


async def evaluate(launcher: SessionLauncher, user_id: str, assessment_id: str) -> BlindStarted:
    async def reserve(db: AsyncSession, session_id: str) -> None:
        row = await BlindAssessments(db, user_id).require(assessment_id)
        if await _stage(db, row) not in {"draft", "failed"}:
            raise AppError(
                "blind_evaluation_started",
                "This assessment is in progress or already evaluated.",
                409,
            )
        row.session_id = session_id
        row.stage = "evaluating"

    session_id = await launcher.start(
        user_id,
        BLIND_GRAPH,
        {"assessment_id": assessment_id},
        subject_type=BLIND_GRAPH,
        subject_id=assessment_id,
        prepare=reserve,
    )
    return BlindStarted(session_id=session_id)
