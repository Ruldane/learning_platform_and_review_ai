"""Créer le brief du jour local (P11, P12, D162), à l'ouverture (`GET /brief/today`) ou à l'heure
réglée (tâche du matin) : jamais deux briefs pour le même jour, jamais deux sessions.

Sous le verrou de l'utilisatrice : le jour est celui de January (`brief_day`, jamais `now.date()`),
le brief existant est rendu tel quel ; sinon les rubriques du code sont calculées et insérées par
`INSERT … ON CONFLICT DO NOTHING` (unicité `(user_id, day)`). **Seul l'inserteur lance** la session
`daily_brief` (sujet `brief`) et pose `session_id` ; un lancement refusé (moteur absent, session
impossible) laisse le conseil `unavailable` (définitif pour la journée) et les rubriques du code
intactes. Rien n'attend un agent : la session tourne en tâche de fond. Journaux : identifiants,
codes ; jamais une rubrique."""

import logging
from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import user_zone
from app.core.errors import AppError
from app.db.models.daily import BriefOrigin
from app.features.brief.repository import BriefRepository
from app.features.brief.schemas import BriefOut
from app.features.brief.service.rules import brief_day
from app.features.brief.service.runtime import GRAPH, SUBJECT, BriefRuntime
from app.features.brief.service.sections import build_sections
from app.features.brief.service.views import brief_not_found, brief_out
from app.features.ledger.service.ledger import safe_code
from app.features.settings.service import SettingsService

logger = logging.getLogger(__name__)


async def _insert(
    rt: BriefRuntime, db: AsyncSession, user_id: str, origin: BriefOrigin, now: datetime
) -> tuple[str, bool]:
    """`(id du brief du jour, créé ?)`. Perdre la course contre un autre insérant (autre
    processus) rend le brief de l'autre, `créé` faux."""
    zone = user_zone((await SettingsService(db, user_id).get()).timezone)
    today: date = brief_day(now, zone)
    repo = BriefRepository(db, user_id)
    existing = await repo.by_day(today)
    if existing is not None:
        return existing.id, False
    sections = await build_sections(rt, db, user_id, today)
    keys = [str(item["key"]) for item in sections["offers"]["items"]]
    created = await repo.insert_if_absent(
        day=today, origin=origin, sections=sections, offer_keys=keys, now=now
    )
    await db.commit()
    if created is not None:
        return created, True
    rival = await repo.by_day(today)
    if rival is None:  # impossible : le conflit vient d'une ligne de ce jour
        raise brief_not_found()
    return rival.id, False


async def _launch(rt: BriefRuntime, user_id: str, brief_id: str) -> None:
    """Lance la session du conseil et la pose sur le brief ; un refus rend le conseil
    `unavailable`."""
    try:
        session_id = await rt.launcher.start(
            user_id, GRAPH, {"brief_id": brief_id}, subject_type=SUBJECT, subject_id=brief_id
        )
    except Exception as exc:
        code = exc.code if isinstance(exc, AppError) else type(exc).__name__
        async with rt.session_factory() as db:
            await BriefRepository(db, user_id).close_advice(brief_id, "unavailable")
            await db.commit()
        logger.warning("Brief sans session : brief %s, cause %s", brief_id, safe_code(code))
        return
    async with rt.session_factory() as db:
        await BriefRepository(db, user_id).set_session(brief_id, session_id)
        await db.commit()
    logger.info("Brief lancé : utilisateur %s, brief %s, session %s", user_id, brief_id, session_id)


async def ensure_today(
    rt: BriefRuntime, user_id: str, *, origin: BriefOrigin, now: datetime | None = None
) -> tuple[BriefOut, bool]:
    """Le brief du jour local de l'utilisatrice (créé s'il manque) et `créé ?`. `now` : l'instant
    de la tâche planifiée ; sans lui, l'horloge du runtime."""
    moment = now or rt.now()
    async with rt.ensure_lock(user_id):
        async with rt.session_factory() as db:
            brief_id, created = await _insert(rt, db, user_id, origin, moment)
        if created:
            await _launch(rt, user_id, brief_id)
    async with rt.session_factory() as db:
        out = await brief_out(rt, db, user_id, brief_id)
    logger.log(
        logging.INFO if created else logging.DEBUG,
        "Brief du jour : brief %s, créé %s, origine %s",
        brief_id,
        created,
        origin,
    )
    return out, created
