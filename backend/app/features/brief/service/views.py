"""Lecture du brief du jour (14.2, D162) : le brief rendu par l'API, avec le statut du conseil à
jour. Un conseil `pending` dont la session n'est plus ouverte (échec, annulation, redémarrage sans
reprise, session perdue) passe en `failed` à la lecture : le statut suit la session, comme le relevé
du radar. `failed` et `unavailable` sont définitifs pour la journée (le port ignore toute écriture
ultérieure) : le front n'a aucun « Réessayer » à offrir. Journaux : identifiants seulement."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models.daily import Brief
from app.features.brief.repository import BriefRepository
from app.features.brief.schemas import BriefOut
from app.features.brief.service.runtime import GRAPH, SUBJECT, BriefRuntime
from app.features.sessions.service import list_open_sessions_by_subject

logger = logging.getLogger(__name__)

# Le temps de lancer la session après la création : sans session au-delà, le lancement a été
# interrompu (arrêt du processus) et le conseil ne viendra pas.
LAUNCH_GRACE = timedelta(minutes=5)


def brief_not_found() -> AppError:
    return AppError("brief_not_found", "Brief introuvable.", 404)


def out_of(row: Brief) -> BriefOut:
    """Le brief rendu : `resource` rangée vide (`{}`) ou absente = `None`, le conseil est la liste
    de ses deux phrases. Les détails internes des rubriques (`key`, `best_quiz`) sont ignorés."""
    sections: dict[str, Any] = row.sections
    advice = (row.advice or {}).get("sentences")
    return BriefOut.model_validate(
        {
            "id": row.id,
            "day": row.day,
            "origin": row.origin,
            "generated_at": row.created_at,
            "block": sections.get("block"),
            "reviews": sections["reviews"],
            "reminders": sections["reminders"],
            "offers": sections["offers"],
            "week": sections.get("week"),
            "resource": row.resource or None,
            "unavailable": sections.get("unavailable", []),
            "advice": advice,
            "advice_status": row.advice_status,
            "session_id": row.session_id,
        }
    )


async def _session_is_dead(rt: BriefRuntime, db: AsyncSession, user_id: str, row: Brief) -> bool:
    if row.session_id is None:
        return rt.now() - row.created_at > LAUNCH_GRACE
    open_ids = await list_open_sessions_by_subject(db, user_id, graph=GRAPH, subject_type=SUBJECT)
    return row.session_id not in open_ids.get(row.id, [])


async def settle(rt: BriefRuntime, db: AsyncSession, user_id: str, row: Brief) -> None:
    """Un conseil `pending` sans session ouverte passe en `failed`. La session est lue AVANT
    l'écriture, qui ne change que ce qui est encore `pending` : un conseil rangé entre-temps reste
    `ready`."""
    if row.advice_status != "pending" or not await _session_is_dead(rt, db, user_id, row):
        return
    if await BriefRepository(db, user_id).close_advice(row.id, "failed"):
        await db.commit()
        logger.info("Brief sans session : utilisateur %s, brief %s", user_id, row.id)


async def brief_out(rt: BriefRuntime, db: AsyncSession, user_id: str, brief_id: str) -> BriefOut:
    repo = BriefRepository(db, user_id)
    row = await repo.get_fresh(brief_id)
    if row is None:
        raise brief_not_found()
    if row.advice_status == "pending":
        await settle(rt, db, user_id, row)
        row = await repo.get_fresh(brief_id) or row
    return out_of(row)


@dataclass(frozen=True)
class RecentBrief:
    id: str
    at: datetime


async def recent_briefs(
    db: AsyncSession, user_id: str, after: datetime | None, before: datetime | None, limit: int
) -> list[RecentBrief]:
    """Les briefs créés dans `[after, before]`, le plus récent d'abord (fil d'activité, 8.7)."""
    rows = await BriefRepository(db, user_id).created_between(after, before, limit)
    return [RecentBrief(id=row.id, at=row.created_at) for row in rows]
