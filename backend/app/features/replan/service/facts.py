"""Faits d'une semaine du programme pour le bilan hebdomadaire (SPEC F13) : temps prévu et fait,
tâches, retard, quiz notés, avance prise, temps d'étude et captures. La semaine est celle de
January (lundi → dimanche dans son fuseau, D98) ; les tâches comptent par leur jour prévu."""

from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import user_zone
from app.features.program.service.programs import load
from app.features.replan.repository import FactsRepository, ReviewRepository
from app.features.replan.service.review import WeekFacts
from app.features.settings.service import SettingsService

DAYS = 7


def _utc(day: date, zone_name: str) -> datetime:
    """Minuit du jour `day` chez January, en UTC."""
    return datetime.combine(day, time(0), tzinfo=user_zone(zone_name)).astimezone(UTC)


async def week_facts(
    db: AsyncSession, user_id: str, program_id: str, week_start: date
) -> WeekFacts:
    """Les faits de la semaine qui commence le lundi `week_start` ; 404 si le programme est à
    un autre."""
    loaded = await load(db, user_id, program_id)
    end = week_start + timedelta(days=DAYS)
    week = [t for t in loaded.tasks if week_start <= t.planned_date < end]
    done = [t for t in week if t.status == "done"]
    ahead = [
        t
        for t in loaded.tasks
        if end <= t.planned_date < end + timedelta(days=DAYS) and t.status == "done"
    ]
    zone = (await SettingsService(db, user_id).get()).timezone
    start_utc, end_utc = _utc(week_start, zone), _utc(end, zone)
    facts = FactsRepository(db, user_id)
    return WeekFacts(
        week_start=week_start,
        planned_minutes=sum(t.minutes for t in week),
        done_minutes=sum(t.minutes for t in done),
        tasks_planned=len(week),
        tasks_done=len(done),
        late_minutes=sum(t.minutes for t in week if t.status != "done"),
        quiz_scores=await facts.quiz_scores(program_id, start_utc, end_utc),
        done_ahead=len(ahead),
        study_minutes=await facts.study_minutes(program_id, start_utc, end_utc),
        captures=await ReviewRepository(db, user_id).captures(week_start, end - timedelta(days=1)),
    )
