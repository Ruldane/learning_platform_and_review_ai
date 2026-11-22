"""Lecteur local des engagements échus pour les routines de ce compte."""

from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.dated_commitments import DatedCommitment
from app.features.dated_commitments import repository
from app.features.dated_commitments.schemas import CommitmentReminder as CommitmentReminder


def summary(row: DatedCommitment) -> CommitmentReminder:
    delta = Decimal(row.observed) - Decimal(row.target) if row.observed is not None else None
    return CommitmentReminder(
        id=row.id,
        title=row.title,
        version=row.version,
        intention=row.intention,
        due_on=row.due_on,
        indicator=row.indicator,
        unit=row.unit,
        delta=delta,
        reviewed=row.observed is not None,
    )


async def due_reminders(
    db: AsyncSession, user_id: str, today: date, *, limit: int = 5
) -> list[CommitmentReminder]:
    """Échéances ouvertes et écarts d’aujourd’hui ou d’hier, au plus cinq."""
    rows = await repository.reminders(db, user_id, today, min(max(limit, 0), 5))
    return [summary(row) for row in rows]
