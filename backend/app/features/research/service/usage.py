"""Brave monthly cap (SPEC 11.3): 900 requests per UTC calendar month and per key."""

import hashlib
import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import SecretUnreadable
from app.features.research.repository import SearchUsageRepository, month_total
from app.features.research.service.errors import BRAVE_MONTHLY_CAP
from app.providers.llm.base import KeyReader

logger = logging.getLogger(__name__)

BRAVE = "brave"


def key_fingerprint(api_key: str) -> str:
    """Short fingerprint of the key (never the key): one counter per key, not per user."""
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:16]


def month_of(now: datetime) -> str:
    """UTC calendar month, "YYYY-MM"."""
    return now.astimezone(UTC).strftime("%Y-%m")


async def brave_key(keys: KeyReader, user_id: str) -> str | None:
    """The current Brave key (settings, otherwise `.env`); an unreadable key counts as absent."""
    try:
        return await keys.get_key(user_id, BRAVE)
    except SecretUnreadable:
        logger.warning("Brave key unreadable, Brave skipped (user %s)", user_id)
        return None


@dataclass(frozen=True)
class BraveReservation:
    """Brave request reserved: enough to give it back to the right counter (month, key)."""

    fingerprint: str
    month: str


async def reserve_brave(
    db: AsyncSession, user_id: str, api_key: str, now: datetime
) -> BraveReservation | None:
    """Reserves a Brave request of the month if the key is under the cap, and commits it at once
    (own transaction, closed before the network call). Indivisible check and increment
    (`SearchUsageRepository.reserve`). `None`: cap reached."""
    reservation = BraveReservation(key_fingerprint(api_key), month_of(now))
    repo = SearchUsageRepository(db, user_id)
    reserved = await repo.reserve(
        BRAVE, reservation.month, reservation.fingerprint, BRAVE_MONTHLY_CAP
    )
    await db.commit()
    return reservation if reserved else None


async def release_brave(db: AsyncSession, user_id: str, reservation: BraveReservation) -> bool:
    """Gives back a request that Brave neither served nor billed (429, key refused, nothing
    sent), in its own short transaction; never below zero (`SearchUsageRepository.release`)."""
    released = await SearchUsageRepository(db, user_id).release(
        BRAVE, reservation.month, reservation.fingerprint
    )
    await db.commit()
    return released


@dataclass(frozen=True)
class BraveUsage:
    has_key: bool
    used: int
    cap: int
    month: str


async def brave_usage(db: AsyncSession, keys: KeyReader, user_id: str, now: datetime) -> BraveUsage:
    """Brave requests of the month for the user's current key (0 without a key)."""
    month = month_of(now)
    api_key = await brave_key(keys, user_id)
    if api_key is None:
        return BraveUsage(has_key=False, used=0, cap=BRAVE_MONTHLY_CAP, month=month)
    used = await month_total(db, provider=BRAVE, month=month, fingerprint=key_fingerprint(api_key))
    return BraveUsage(has_key=True, used=used, cap=BRAVE_MONTHLY_CAP, month=month)
