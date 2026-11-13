"""Bilan hebdomadaire planifié (SPEC F13, 11.4 ; D106) : appelé par la tâche planifiée
`weekly_review` (`app.scheduler`, qui n'est jamais importé ici : contrat 8).

Pour chaque programme validé (lecture sans `user_id`, D18, D91, puis tout sous l'utilisateur) :
le jour du bilan est le dernier `weekly_review.day` au plus aujourd'hui chez January, l'heure
`weekly_review.time` dans son fuseau (D98). L'heure passée, la semaine relue est celle qui finit
le jour du bilan (dimanche) ou la précédente : `week_start(jour − 6 jours)`. Le bilan est une
ligne `weekly_review` du journal, clé « review:{programme}:{semaine} » (idempotent) ; puis une
session `replan` est lancée pour lui s'il reste des semaines, si aucune replanification n'est
ouverte et si aucune ne l'a déjà été pour ce bilan (un lancement refusé est repris au passage
suivant). Une panne sur un programme n'arrête pas les autres. Journaux : identifiants seulement."""

import logging
from dataclasses import asdict
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.clock import WEEKDAYS, Weekday, local_moment, local_today, user_zone, week_start
from app.features.capture.service.journal import add_entry
from app.features.program.service.programs import Loaded, list_validated_programs, load
from app.features.replan.repository import ReplanSessionRepository, ReviewRepository
from app.features.replan.service.facts import week_facts
from app.features.replan.service.launch import open_replan
from app.features.replan.service.review import WeekFacts, classify, late_ratio, review_text
from app.features.replan.service.runtime import GRAPH, SUBJECT, ReplanRuntime
from app.features.settings.service import SettingsService

logger = logging.getLogger(__name__)

DAYS = 7


def review_day(today: date, day: Weekday) -> date:
    """Le dernier jour `day` au plus `today`."""
    return today - timedelta(days=(today.weekday() - WEEKDAYS[day]) % DAYS)


def review_key(program_id: str, week: date) -> str:
    return f"review:{program_id}:{week.isoformat()}"


def _covers(loaded: Loaded, week: date) -> bool:
    """La semaine du lundi `week` touche-t-elle le programme ?"""
    if not loaded.weeks:
        return False
    return loaded.weeks[0].start_date < week + timedelta(days=DAYS) and (
        week <= loaded.weeks[-1].start_date + timedelta(days=DAYS - 1)
    )


async def _previous_ratio(
    db: AsyncSession, user_id: str, loaded: Loaded, week: date
) -> float | None:
    """Le retard de la semaine d'avant : celui de son bilan, sinon recalculé, `None` hors du
    programme."""
    previous = week - timedelta(days=DAYS)
    entry = await ReviewRepository(db, user_id).by_key(review_key(loaded.program.id, previous))
    if entry is not None and isinstance(entry.data.get("ratio"), int | float):
        return float(entry.data["ratio"])
    if not _covers(loaded, previous):
        return None
    return late_ratio(await week_facts(db, user_id, loaded.program.id, previous))


def _data(program_id: str, facts: WeekFacts, state: str, ratio: float) -> dict[str, Any]:
    raw = asdict(facts)
    raw["week_start"] = facts.week_start.isoformat()
    return {**raw, "program_id": program_id, "state": state, "ratio": ratio}


async def _write_review(
    db: AsyncSession, user_id: str, loaded: Loaded, week: date, day: date
) -> str:
    facts = await week_facts(db, user_id, loaded.program.id, week)
    ratio = late_ratio(facts)
    state = classify(facts, await _previous_ratio(db, user_id, loaded, week))
    return await add_entry(
        db,
        user_id,
        kind="weekly_review",
        text=review_text(facts),
        occurred_on=day,
        ref_key=review_key(loaded.program.id, week),
        data=_data(loaded.program.id, facts, state, ratio),
    )


async def _launch(rt: ReplanRuntime, user_id: str, program_id: str, entry_id: str) -> bool:
    async with rt.launch_lock(user_id, program_id):
        async with rt.session_factory() as db:
            done = await ReplanSessionRepository(db, user_id).launched_for(program_id, entry_id)
            busy = await open_replan(db, user_id, program_id)
        if done or busy is not None:
            return False
        payload = {
            "program_id": program_id,
            "trigger": "weekly_review",
            "review_entry_id": entry_id,
        }
        await rt.launcher.start(
            user_id, GRAPH, payload, subject_type=SUBJECT, subject_id=program_id
        )
    return True


async def review_program(rt: ReplanRuntime, user_id: str, program_id: str, now: datetime) -> bool:
    """Écrit le bilan dû de ce programme et lance sa replanification ; rend vrai si le bilan
    vient d'être écrit."""
    async with rt.session_factory() as db:
        stored = await SettingsService(db, user_id).get()
        zone, when = user_zone(stored.timezone), stored.weekly_review
        day = review_day(local_today(zone, now), when.day)
        if now < local_moment(day, when.time, zone):
            return False
        week = week_start(day - timedelta(days=DAYS - 1))
        loaded = await load(db, user_id, program_id)
        if not _covers(loaded, week):
            return False
        entry = await ReviewRepository(db, user_id).by_key(review_key(program_id, week))
        written = entry is None
        entry_id = (
            entry.id if entry is not None else await _write_review(db, user_id, loaded, week, day)
        )
        await db.commit()
        remaining = loaded.weeks[-1].start_date > week
    if remaining:
        try:
            await _launch(rt, user_id, program_id, entry_id)
        except Exception as exc:  # repris au passage suivant ; le bilan reste écrit
            logger.warning(
                "Bilan hebdomadaire : replanification de %s non lancée (%s)",
                program_id,
                type(exc).__name__,
            )
    return written


async def run_weekly_reviews(
    session_factory: async_sessionmaker[AsyncSession], runtime: ReplanRuntime, now: datetime
) -> int:
    """Un passage de la tâche planifiée ; rend le nombre de bilans écrits."""
    async with session_factory() as db:
        programs = await list_validated_programs(db)
    written = 0
    for user_id, program_id in programs:
        try:
            written += await review_program(runtime, user_id, program_id, now)
        except Exception as exc:
            logger.warning(
                "Bilan hebdomadaire : programme %s non traité (%s)", program_id, type(exc).__name__
            )
    level = logging.INFO if written else logging.DEBUG
    logger.log(level, "Bilan hebdomadaire : %d programme(s), %d bilan(s)", len(programs), written)
    return written
