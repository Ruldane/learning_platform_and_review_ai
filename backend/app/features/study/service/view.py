"""Lectures de l'étude guidée (D103 n° 4, 5) : l'état d'une session (écran de fin) et le résumé
(série, heures de la semaine, minuteur, session ouverte, bloc du jour). Jours et semaines locaux
(fuseau de January, D98).

Une session `open` dont la session d'agents est terminée (échec, annulation) ou introuvable est
montrée `interrupted`, sans écriture (D91, F11) ; la base n'est corrigée que sous le verrou de
l'utilisatrice (nouveau départ, « Terminer »). Ordre des lectures (D97 n° 9) : la session
d'agents, PUIS la ligne relue : une session finie entre les deux lectures n'est jamais montrée
interrompue."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_today, user_zone, week_start
from app.db.models.study import StudySession
from app.features.sessions.service import session_facts
from app.features.settings.service import SettingsService
from app.features.study.repository import StudyReadRepository, StudyRepository
from app.features.study.schemas import StudySessionOut, StudySummaryOut
from app.features.study.service.block import block_of_day
from app.features.study.service.finish import finished_of, study_not_found
from app.features.study.service.runtime import StudyRuntime
from app.features.study.service.streak import streak

TERMINAL = frozenset({"completed", "failed", "cancelled"})


async def agent_status(db: AsyncSession, user_id: str, session_id: str | None) -> str | None:
    """Statut de la session d'agents (`None` : pas encore rangée, ou introuvable)."""
    if session_id is None:
        return None
    facts = await session_facts(db, user_id, session_id)
    return facts.status if facts is not None else "missing"


def is_dead(row: StudySession, status: str | None) -> bool:
    """Session encore `open` dont la session d'agents ne tourne plus."""
    return (
        row.status == "open" and status is not None and (status in TERMINAL or status == "missing")
    )


async def read_row(
    db: AsyncSession, user_id: str, study_id: str
) -> tuple[StudySession, str | None]:
    """`(ligne, statut de sa session d'agents)` dans l'ordre sûr ; 404 pour celle d'une autre."""
    repo = StudyRepository(db, user_id)
    first = await repo.get_fresh(study_id)
    if first is None:
        raise study_not_found()
    status = await agent_status(db, user_id, first.session_id)
    row = await repo.get_fresh(study_id)
    if row is None:
        raise study_not_found()
    if row.session_id != first.session_id:
        status = await agent_status(db, user_id, row.session_id)
    return row, status


async def session_out(db: AsyncSession, user_id: str, study_id: str) -> StudySessionOut:
    row, status = await read_row(db, user_id, study_id)
    lesson_title, module_title = await StudyReadRepository(db, user_id).titles(
        row.lesson_id, row.module_id
    )
    done = finished_of(row)
    return StudySessionOut.model_validate(
        {
            "id": row.id,
            "lesson_id": row.lesson_id,
            "lesson_title": lesson_title,
            "module_title": module_title,
            "mode": row.mode,
            "status": "interrupted" if is_dead(row, status) else row.status,
            "session_id": row.session_id,
            "started_at": row.created_at,
            "ended_at": row.ended_at,
            "minutes": row.minutes,
            "summary": row.summary,
            "tasks_done": done.tasks_done,
            "flashcards_created": done.flashcards_created,
            "skills": [{"name": name, "level": level} for name, level in done.skills],
        }
    )


def _local(moment: datetime, zone: ZoneInfo) -> datetime:
    return moment.astimezone(zone)


async def summary(rt: StudyRuntime, db: AsyncSession, user_id: str) -> StudySummaryOut:
    settings = await SettingsService(db, user_id).get()
    zone = user_zone(settings.timezone)
    today = local_today(zone, rt.now())
    monday = week_start(today)
    ended = [
        (_local(at, zone).date(), minutes)
        for at, minutes in await StudyRepository(db, user_id).finished()
    ]
    week = sum(m for day, m in ended if monday <= day < monday + timedelta(days=7))
    current = await StudyRepository(db, user_id).open_one()
    block = await block_of_day(db, user_id, today)
    return StudySummaryOut(
        streak_days=streak({day for day, _ in ended}, today),
        week_minutes=week,
        work_minutes=settings.study_work_minutes,
        break_minutes=settings.study_break_minutes,
        open_session_id=current.id if current is not None else None,
        block=block.out() if block is not None else None,
    )
