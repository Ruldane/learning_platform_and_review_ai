from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.clock import local_today, user_zone
from app.core.errors import AppError
from app.db.base import utcnow
from app.db.models.dated_commitments import DatedCommitment
from app.features.dated_commitments import repository
from app.features.dated_commitments.schemas import CommitmentCreate, CommitmentOut, CommitmentReview
from app.features.dated_commitments.service.reminders import summary
from app.features.postings.service.runtime import KeyLocks
from app.features.settings.service import SettingsService


@dataclass
class CommitmentsRuntime:
    factory: async_sessionmaker[AsyncSession]
    locks: KeyLocks = field(default_factory=KeyLocks)


def _amount(value: Decimal) -> str:
    return format(value.normalize(), "f") if value else "0"


async def _owned(db: AsyncSession, user_id: str, commitment_id: str) -> DatedCommitment:
    row = await repository.by_id(db, user_id, commitment_id)
    if row is None:
        raise AppError("commitment_not_found", "Engagement introuvable.", 404)
    return row


def _status(row: DatedCommitment, today: date) -> Literal["scheduled", "due", "reviewed"]:
    if row.observed is not None:
        return "reviewed"
    return "due" if row.due_on <= today else "scheduled"


def _view(row: DatedCommitment, today: date) -> CommitmentOut:
    return CommitmentOut(
        **summary(row).model_dump(),
        status=_status(row, today),
        target=Decimal(row.target),
        observed=Decimal(row.observed) if row.observed is not None else None,
        note=row.note,
        created_at=row.created_at,
        reviewed_at=row.reviewed_at,
    )


async def _day(db: AsyncSession, user_id: str, now: datetime | None = None) -> date:
    settings = await SettingsService(db, user_id).get()
    return local_today(user_zone(settings.timezone), utcnow() if now is None else now)


async def list_commitments(db: AsyncSession, user_id: str) -> list[CommitmentOut]:
    today = await _day(db, user_id)
    return [_view(row, today) for row in await repository.list_for_user(db, user_id)]


async def read(db: AsyncSession, user_id: str, commitment_id: str) -> CommitmentOut:
    return _view(await _owned(db, user_id, commitment_id), await _day(db, user_id))


async def create(rt: CommitmentsRuntime, user_id: str, action: CommitmentCreate) -> CommitmentOut:
    request_id = str(action.request_id)
    fields = action.model_dump(exclude={"request_id"})
    fields["target"] = _amount(action.target)
    async with rt.locks.get(user_id, request_id), rt.factory() as db:
        today = await _day(db, user_id)
        row = await repository.by_request(db, user_id, request_id)
        if row is not None:
            if any(getattr(row, name) != value for name, value in fields.items()):
                raise AppError("commitment_request_used", "This draft has already been saved.", 409)
            return _view(row, today)
        row = DatedCommitment(user_id=user_id, request_id=request_id, **fields)
        db.add(row)
        await db.commit()
        return _view(row, today)


async def review(
    rt: CommitmentsRuntime, user_id: str, commitment_id: str, action: CommitmentReview
) -> CommitmentOut:
    observed, note = _amount(action.observed), action.note or None
    async with rt.locks.get(user_id, commitment_id), rt.factory() as db:
        row = await _owned(db, user_id, commitment_id)
        now = utcnow()
        today = await _day(db, user_id, now)
        if row.observed is not None:
            if row.observed == observed and row.note == note:
                return _view(row, today)
            raise AppError("commitment_reviewed", "The measurement is already recorded.", 409)
        if row.due_on > today:
            raise AppError("commitment_not_due", "This commitment is not due yet.", 409)
        row.observed, row.note = observed, note
        row.reviewed_on, row.reviewed_at = today, now
        await db.commit()
        return _view(row, today)
