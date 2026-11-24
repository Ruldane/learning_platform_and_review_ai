from collections import defaultdict
from dataclasses import dataclass, field
from unicodedata import normalize

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import AppError
from app.core.practice import content_version
from app.db.base import new_id, utcnow
from app.db.models.error_atlas import AtlasHypothesis, AtlasObservation
from app.features.error_atlas import evidence, repository
from app.features.error_atlas.schemas import (
    AtlasEvidenceOut,
    AtlasExerciseOut,
    AtlasHypothesisOut,
    AtlasObservationIn,
    AtlasObservationOut,
)
from app.features.postings.service.runtime import KeyLocks


@dataclass
class AtlasRuntime:
    factory: async_sessionmaker[AsyncSession]
    locks: KeyLocks = field(default_factory=KeyLocks)


def _exercise(row: AtlasHypothesis) -> AtlasExerciseOut | None:
    return AtlasExerciseOut.model_validate(row.exercise) if row.exercise is not None else None


def _view(row: AtlasHypothesis, observations: list[AtlasObservation]) -> AtlasHypothesisOut:
    items = [
        AtlasObservationOut.model_validate(
            {
                "id": observation.id,
                "confidence": observation.confidence,
                "evidence": observation.evidence,
            }
        )
        for observation in observations
    ]
    levels = {item.confidence for item in items}
    return AtlasHypothesisOut(
        id=row.id,
        label=row.label,
        confidence=levels.pop() if len(levels) == 1 else "mixed",
        observations=items,
        exercise=_exercise(row),
    )


async def list_hypotheses(db: AsyncSession, user_id: str) -> list[AtlasHypothesisOut]:
    groups: dict[str, list[AtlasObservation]] = defaultdict(list)
    for row in await repository.observations(db, user_id):
        groups[row.hypothesis_id].append(row)
    return [_view(row, groups[row.id]) for row in await repository.list_hypotheses(db, user_id)]


async def observe(rt: AtlasRuntime, user_id: str, action: AtlasObservationIn) -> AtlasHypothesisOut:
    label = " ".join(action.hypothesis.split())
    key = content_version(normalize("NFKC", label).casefold())
    evidence_key = content_version(action.reference.model_dump())
    async with rt.locks.get(user_id, "atlas"), rt.factory() as db:
        row = await repository.matching_label(db, user_id, key)
        observed = await repository.observations(db, user_id, row.id) if row else []
        if row is not None and any(item.evidence_key == evidence_key for item in observed):
            return _view(row, observed)

        verified = await evidence.read_evidence(db, user_id, action.reference)
        if row is None:
            row = AtlasHypothesis(id=new_id(), user_id=user_id, label=label, label_key=key)
            db.add(row)
            await db.flush()
        observation = AtlasObservation(
            user_id=user_id,
            hypothesis_id=row.id,
            evidence_key=evidence_key,
            evidence=verified.model_dump(mode="json"),
            confidence=action.confidence,
        )
        db.add(observation)
        await db.commit()
        return _view(row, [*observed, observation])


def _steps(sources: list[AtlasEvidenceOut]) -> list[str]:
    steps = ["From the cited gradings, state the prerequisite rule in one sentence."]
    kinds = {source.reference.kind for source in sources}
    if "quiz" in kinds:
        steps.append(
            "Make up a new question that puts this rule to the test. Answer before "
            "comparing your reasoning with the grading's."
        )
    if "project" in kinds:
        steps.append(
            "Build a minimal case where the project criterion fails. Write down the expected "
            "result, fix the case on a copy, then check the result."
        )
    steps.append(
        "Add a counterexample that tells the corrected rule apart from the initial reasoning."
    )
    return steps


async def start_exercise(rt: AtlasRuntime, user_id: str, hypothesis_id: str) -> AtlasExerciseOut:
    async with rt.locks.get(user_id, "atlas"), rt.factory() as db:
        row = await repository.hypothesis(db, user_id, hypothesis_id)
        if row is None:
            raise AppError("atlas_hypothesis_not_found", "Hypothesis not found.", 404)
        if stored := _exercise(row):
            return stored
        observations = await repository.observations(db, user_id, row.id)
        sources = [AtlasEvidenceOut.model_validate(item.evidence) for item in observations]
        exercise = AtlasExerciseOut(
            id=new_id(), created_at=utcnow(), steps=_steps(sources), evidence=sources
        )
        row.exercise = exercise.model_dump(mode="json")
        await db.commit()
        return exercise
