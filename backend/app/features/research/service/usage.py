"""Plafond mensuel de Brave (SPEC 11.3) : 900 requêtes par mois civil UTC et par clé."""

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
    """Empreinte courte de la clé (jamais la clé) : un compteur par clé, pas par utilisateur."""
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:16]


def month_of(now: datetime) -> str:
    """Mois civil UTC, « AAAA-MM »."""
    return now.astimezone(UTC).strftime("%Y-%m")


async def brave_key(keys: KeyReader, user_id: str) -> str | None:
    """Clé Brave en vigueur (réglages, sinon `.env`) ; une clé illisible compte comme absente."""
    try:
        return await keys.get_key(user_id, BRAVE)
    except SecretUnreadable:
        logger.warning("Clé Brave illisible, Brave sauté (utilisateur %s)", user_id)
        return None


@dataclass(frozen=True)
class BraveReservation:
    """Requête Brave réservée : de quoi la rendre au bon compteur (même mois, même clé)."""

    fingerprint: str
    month: str


async def reserve_brave(
    db: AsyncSession, user_id: str, api_key: str, now: datetime
) -> BraveReservation | None:
    """Réserve une requête Brave du mois si la clé est sous le plafond, et la commite aussitôt
    (transaction propre, fermée avant l'appel réseau). Contrôle et ajout indivisibles
    (`SearchUsageRepository.reserve`). `None` : plafond atteint."""
    reservation = BraveReservation(key_fingerprint(api_key), month_of(now))
    repo = SearchUsageRepository(db, user_id)
    reserved = await repo.reserve(
        BRAVE, reservation.month, reservation.fingerprint, BRAVE_MONTHLY_CAP
    )
    await db.commit()
    return reservation if reserved else None


async def release_brave(db: AsyncSession, user_id: str, reservation: BraveReservation) -> bool:
    """Rend une requête que Brave n'a ni servie ni facturée (429, clé refusée, rien d'envoyé),
    dans sa propre transaction courte ; jamais sous zéro (`SearchUsageRepository.release`)."""
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
    """Requêtes Brave du mois pour la clé en vigueur de l'utilisateur (0 sans clé)."""
    month = month_of(now)
    api_key = await brave_key(keys, user_id)
    if api_key is None:
        return BraveUsage(has_key=False, used=0, cap=BRAVE_MONTHLY_CAP, month=month)
    used = await month_total(db, provider=BRAVE, month=month, fingerprint=key_fingerprint(api_key))
    return BraveUsage(has_key=True, used=used, cap=BRAVE_MONTHLY_CAP, month=month)
