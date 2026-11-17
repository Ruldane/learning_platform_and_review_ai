"""Rafraîchissement de la base ATS (P14, D158) : appelé par la tâche planifiée `ats_refresh`
(`app.scheduler`, jamais importé ici : contrat 8).

Chaque compte est dû quand aucun passage `done` n'a fini il y a moins de 30 jours. Le passage se
gagne dans le registre (`claim`, période = jour local de January, D98) ; puis une session
`web_research` est lancée avec une requête fixe sur le fonctionnement des ATS (sujet
`ats_refresh`). Le Lecteur ATS relit ensuite ses sources retenues (`review_store.ats_updates`).
Un lancement refusé est rangé sous son code (type d'erreur ou code d'`AppError`, jamais le
message) et repris au passage suivant, 3 essais par jour. Une panne pour un compte n'arrête pas
les autres. Journaux : identifiants, nombres et codes seulement."""

import logging
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.launcher import SessionLauncher
from app.core.clock import local_today, user_zone
from app.core.errors import AppError
from app.features.ledger.service.ledger import (
    Claim,
    JobRunView,
    claim,
    fail,
    finish,
    last_done,
    reopen,
    scheduled_user_ids,
)
from app.features.ledger.service.periods import ATS_EVERY_DAYS, day_period
from app.features.sessions.service import session_facts
from app.features.settings.service import SettingsService

logger = logging.getLogger(__name__)

JOB = "ats_refresh"
GRAPH = "web_research"
SUBJECT = "ats_refresh"
ATS_QUERY = (
    "fonctionnement logiciels ATS recrutement Greenhouse Workday Lever Teamtailor nouveautés"
)


def _code(exc: Exception) -> str:
    return exc.code if isinstance(exc, AppError) else type(exc).__name__


SESSION_FAILED = "session_failed"
_MAX_REOPENED = 5


async def _last_good_done(db: AsyncSession, user_id: str, now: datetime) -> JobRunView | None:
    """Le dernier passage `done` dont la session n'a pas échoué. Un passage `done` est écrit dès
    le lancement : si sa session est ensuite `failed`, il compte comme non fait (il repasse en
    `failed` dans le registre : repris au passage suivant, dans la limite des essais)."""
    for _ in range(_MAX_REOPENED):
        last = await last_done(db, user_id, JOB)
        if last is None or last.ref_id is None:
            return last
        facts = await session_facts(db, user_id, last.ref_id)
        if facts is None or facts.status != "failed":
            return last
        await reopen(db, user_id, last, code=SESSION_FAILED, now=now)
        await db.commit()
    return None


async def _claim_due(db: AsyncSession, user_id: str, now: datetime) -> Claim | None:
    """Le passage gagné si ce compte est dû, sinon `None` (déjà fait il y a moins de 30 jours,
    ou période déjà prise)."""
    last = await _last_good_done(db, user_id, now)
    finished = last.finished_at if last is not None else None
    if finished is not None and now - finished < timedelta(days=ATS_EVERY_DAYS):
        return None
    zone = user_zone((await SettingsService(db, user_id).get()).timezone)
    got = await claim(db, user_id, JOB, day_period(local_today(zone, now)), now)
    await db.commit()
    return got


async def _refresh(
    session_factory: async_sessionmaker[AsyncSession],
    launcher: SessionLauncher,
    user_id: str,
    now: datetime,
) -> bool:
    async with session_factory() as db:
        got = await _claim_due(db, user_id, now)
    if got is None:
        return False
    try:
        session_id = await launcher.start(
            user_id, GRAPH, {"query": ATS_QUERY}, subject_type=SUBJECT
        )
    except Exception as exc:
        async with session_factory() as db:
            await fail(db, user_id, got.run_id, attempt=got.attempt, code=_code(exc), now=now)
            await db.commit()
        logger.warning("Rafraîchissement ATS : utilisateur %s, lancement refusé", user_id)
        return False
    async with session_factory() as db:
        await finish(
            db,
            user_id,
            got.run_id,
            attempt=got.attempt,
            status="done",
            now=now,
            ref_id=session_id,
            next_due_at=now + timedelta(days=ATS_EVERY_DAYS),
        )
        await db.commit()
    logger.info("Rafraîchissement ATS : utilisateur %s, session %s", user_id, session_id)
    return True


async def run_ats_refresh(
    session_factory: async_sessionmaker[AsyncSession], launcher: SessionLauncher, now: datetime
) -> int:
    """Un passage de la tâche planifiée ; rend le nombre de sessions lancées."""
    async with session_factory() as db:
        users = await scheduled_user_ids(db)
    launched = 0
    for user_id in users:
        try:
            launched += await _refresh(session_factory, launcher, user_id, now)
        except Exception as exc:
            logger.warning(
                "Rafraîchissement ATS : utilisateur %s non traité (%s)", user_id, type(exc).__name__
            )
    level = logging.INFO if launched else logging.DEBUG
    logger.log(level, "Rafraîchissement ATS : %d compte(s), %d session(s)", len(users), launched)
    return launched
