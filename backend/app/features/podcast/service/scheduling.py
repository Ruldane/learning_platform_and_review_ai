"""Le passage quotidien se réserve dans le registre déjà utilisé par le brief."""

from datetime import datetime

from app.core.clock import local_today, user_zone
from app.core.errors import AppError
from app.features.brief.service.rules import brief_due
from app.features.ledger.service.ledger import claim, fail, finish, scheduled_user_ids
from app.features.ledger.service.periods import day_period
from app.features.podcast.service.launch import start_episode
from app.features.podcast.service.runtime import PodcastRuntime
from app.features.settings.service import SettingsService

JOB = "podcast_daily"


async def _run_one(rt: PodcastRuntime, user_id: str, now: datetime) -> None:
    async with rt.session_factory() as db:
        settings = await SettingsService(db, user_id).get()
        zone = user_zone(settings.timezone)
        if not brief_due(now, zone, settings.brief_time):
            return
        day = local_today(zone, now)
        attempt = await claim(db, user_id, JOB, day_period(day), now)
        await db.commit()
    if attempt is None:
        return
    try:
        session_id = await start_episode(rt, user_id, day)
    except Exception as exc:
        code = exc.code if isinstance(exc, AppError) else type(exc).__name__
        async with rt.session_factory() as db:
            if code == "podcast_no_chapter":
                await finish(
                    db, user_id, attempt.run_id, attempt=attempt.attempt, status="skipped", now=now
                )
            else:
                await fail(db, user_id, attempt.run_id, attempt=attempt.attempt, code=code, now=now)
            await db.commit()
        return
    async with rt.session_factory() as db:
        await finish(
            db,
            user_id,
            attempt.run_id,
            attempt=attempt.attempt,
            status="done",
            now=now,
            ref_id=session_id,
        )
        await db.commit()


async def run_daily_podcasts(rt: PodcastRuntime, now: datetime) -> None:
    async with rt.session_factory() as db:
        users = await scheduled_user_ids(db)
    for user_id in users:
        await _run_one(rt, user_id, now)
