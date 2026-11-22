from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Final

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import AppError
from app.db.base import new_id, utcnow
from app.db.models.missions import Mission
from app.features.missions import repository
from app.features.missions.schemas import (
    Criterion,
    MissionCreate,
    MissionCriterionOut,
    MissionLevel,
    MissionOut,
    MissionProgress,
    MissionStatus,
    MissionSubmissionOut,
    MissionSubmit,
)
from app.features.postings.service.queries import read_posting
from app.features.postings.service.runtime import KeyLocks

TARGET: Final = 2
LEVELS: tuple[MissionLevel, ...] = ("not_started", "in_progress", "achieved")


@dataclass
class MissionRuntime:
    factory: async_sessionmaker[AsyncSession]
    now: Callable[[], datetime] = utcnow
    locks: KeyLocks = field(default_factory=KeyLocks)


def _criteria(mission: Mission) -> list[Criterion]:
    return [Criterion.model_validate(data) for data in mission.criteria]


def _status(mission: Mission, now: datetime) -> MissionStatus:
    if mission.submission is not None:
        return "completed"
    if mission.deadline_at <= now:
        return "expired"
    return "active"


def _view(mission: Mission, now: datetime) -> MissionOut:
    criteria = [
        MissionCriterionOut(
            **criterion.model_dump(), target=TARGET, level=LEVELS[criterion.observed]
        )
        for criterion in _criteria(mission)
    ]
    submission = (
        MissionSubmissionOut.model_validate(mission.submission)
        if mission.submission is not None
        else None
    )
    return MissionOut(
        id=mission.id,
        posting_id=mission.posting_id,
        posting_title=mission.posting_title,
        company=mission.company,
        created_at=mission.created_at,
        deadline_at=mission.deadline_at,
        revision=mission.revision,
        criteria=criteria,
        status=_status(mission, now),
        submission=submission,
    )


async def _owned(db: AsyncSession, user_id: str, mission_id: str) -> Mission:
    mission = await repository.by_id(db, user_id, mission_id)
    if mission is None:
        raise AppError("mission_not_found", "Mission introuvable.", 404)
    return mission


async def count_ending_missions(db: AsyncSession, user_id: str, now: datetime) -> int:
    deadline = now + timedelta(days=1)
    return sum(
        _status(row, now) == "active" and row.deadline_at <= deadline
        for row in await repository.list_for_user(db, user_id)
    )


async def list_missions(rt: MissionRuntime, user_id: str) -> list[MissionOut]:
    async with rt.factory() as db:
        now = rt.now()
        return [_view(mission, now) for mission in await repository.list_for_user(db, user_id)]


async def read_mission(rt: MissionRuntime, user_id: str, mission_id: str) -> MissionOut:
    async with rt.factory() as db:
        return _view(await _owned(db, user_id, mission_id), rt.now())


async def _snapshot(
    db: AsyncSession, user_id: str, action: MissionCreate, now: datetime
) -> Mission:
    posting = await read_posting(db, user_id, str(action.posting_id))
    if posting.status != "ready" or posting.analysis is None:
        raise AppError("posting_not_ready", "L'analyse de l'offre doit être terminée.", 409)
    requirements = posting.analysis.requirements
    if max(action.requirement_indices) >= len(requirements):
        raise AppError(
            "mission_requirement_unknown", "Une exigence sélectionnée est introuvable.", 422
        )
    criteria = [
        Criterion(
            index=index,
            text=requirements[index].text,
            skills=requirements[index].skills,
            required=requirements[index].required,
            observed=0,
            note=None,
        ).model_dump()
        for index in sorted(action.requirement_indices)
    ]
    return Mission(
        user_id=user_id,
        posting_id=posting.id,
        posting_title=posting.title,
        company=posting.company,
        created_at=now,
        updated_at=now,
        deadline_at=now + timedelta(hours=48),
        revision=0,
        criteria=criteria,
    )


async def start_mission(rt: MissionRuntime, user_id: str, action: MissionCreate) -> MissionOut:
    posting_id = str(action.posting_id)
    async with rt.locks.get(user_id, posting_id), rt.factory() as db:
        mission = await repository.by_posting(db, user_id, posting_id)
        now = rt.now()
        if mission is not None:
            if [criterion.index for criterion in _criteria(mission)] != sorted(
                action.requirement_indices
            ):
                raise AppError("mission_exists", "Une mission existe déjà pour cette offre.", 409)
            return _view(mission, now)
        mission = await _snapshot(db, user_id, action, now)
        db.add(mission)
        await db.commit()
        return _view(mission, now)


def _ensure_writable(mission: Mission, revision: int, now: datetime) -> None:
    status = _status(mission, now)
    if status == "completed":
        raise AppError("mission_completed", "Le rendu de cette mission est déjà enregistré.", 409)
    if status == "expired":
        raise AppError("mission_expired", "Les 48 heures de cette mission sont écoulées.", 409)
    if mission.revision != revision:
        raise AppError(
            "mission_changed", "La mission a changé. Recharge-la avant de continuer.", 409
        )


async def update_criterion(
    rt: MissionRuntime, user_id: str, mission_id: str, index: int, action: MissionProgress
) -> MissionOut:
    async with rt.locks.get(user_id, mission_id), rt.factory() as db:
        mission = await _owned(db, user_id, mission_id)
        now = rt.now()
        criteria = _criteria(mission)
        selected = next((criterion for criterion in criteria if criterion.index == index), None)
        if selected is None:
            raise AppError(
                "mission_criterion_unknown", "Critère introuvable dans cette mission.", 404
            )
        note = (action.note or None) if "note" in action.model_fields_set else selected.note
        if selected.observed == action.observed and selected.note == note:
            return _view(mission, now)
        _ensure_writable(mission, action.revision, now)
        selected.observed = action.observed
        selected.note = note
        mission.criteria = [criterion.model_dump() for criterion in criteria]
        mission.revision += 1
        await db.commit()
        return _view(mission, now)


async def submit_mission(
    rt: MissionRuntime, user_id: str, mission_id: str, action: MissionSubmit
) -> MissionOut:
    async with rt.locks.get(user_id, mission_id), rt.factory() as db:
        mission = await _owned(db, user_id, mission_id)
        now = rt.now()
        if mission.submission is not None and mission.submission["artifact"] == action.artifact:
            return _view(mission, now)
        _ensure_writable(mission, action.revision, now)
        if any(criterion.observed != TARGET for criterion in _criteria(mission)):
            raise AppError(
                "mission_incomplete", "Termine les mesures avant d'enregistrer le rendu.", 409
            )
        submission = MissionSubmissionOut(
            proof_id=new_id(), artifact=action.artifact, recorded_at=now
        )
        mission.submission = submission.model_dump(mode="json")
        mission.revision += 1
        await db.commit()
        return _view(mission, now)
