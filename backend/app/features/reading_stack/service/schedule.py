"""Morning collection, resumed by the job registry, with atomic writes."""

import logging
from datetime import datetime
from typing import Any

from app.core.clock import local_today, user_zone
from app.core.errors import AppError
from app.features.brief.service.rules import brief_due
from app.features.ledger.service.ledger import (
    Claim,
    claim,
    fail,
    finish,
    last_done,
    scheduled_user_ids,
)
from app.features.ledger.service.periods import day_period
from app.features.radar.service.views import offers_since
from app.features.reading_stack.repository import ReadingRepository, ReadingSources
from app.features.reading_stack.service.collect import collect_web, usable_url
from app.features.reading_stack.types import CollectedItem
from app.features.research.service.runtime import ResearchRuntime
from app.features.settings.service import SettingsService

logger = logging.getLogger(__name__)
JOB = "reading_stack"
MAX_OFFERS = 15
MAX_SOURCES = 12


def _offer(entry: dict[str, Any]) -> CollectedItem | None:
    url = usable_url(str(entry["url"]))
    title = str(entry.get("title") or "").strip()
    if not url or not title:
        return None
    company = str(entry.get("company") or "").strip()[:160] or None
    return CollectedItem(
        "offer", url, title[:240], company or "", "", f"Radar · {entry['score']} %", company
    )


async def _reserve(rt: ResearchRuntime, user_id: str, now: datetime) -> Claim | None:
    async with rt.session_factory() as db:
        settings = await SettingsService(db, user_id).get()
        zone = user_zone(settings.timezone)
        if not brief_due(now, zone, settings.brief_time):
            return None
        run = await claim(db, user_id, JOB, day_period(local_today(zone, now)), now)
        await db.commit()
        return run


async def _gather(rt: ResearchRuntime, user_id: str) -> list[CollectedItem]:
    async with rt.session_factory() as db:
        prev = await last_done(db, user_id, JOB)
        offers = await offers_since(db, user_id, prev.finished_at if prev is not None else None)
        sources = (await ReadingSources(db, user_id).list(active=True))[:MAX_SOURCES]
        known = await ReadingRepository(db, user_id).recent_urls()
    jobs = [item for raw in offers[:MAX_OFFERS] if (item := _offer(raw)) is not None]
    known.update(item.url for item in jobs)
    return jobs + await collect_web(rt, user_id, sources, known)


async def _run_user(rt: ResearchRuntime, user_id: str, started_at: datetime) -> int:
    running = await _reserve(rt, user_id, started_at)
    if running is None:
        return 0
    try:
        entries = await _gather(rt, user_id)
        async with rt.session_factory() as db:
            repo = ReadingRepository(db, user_id)
            added = sum([await repo.record(item, started_at) is not None for item in entries])
            await finish(
                db, user_id, running.run_id, attempt=running.attempt, status="done", now=rt.now()
            )
            await db.commit()
    except Exception as exc:
        async with rt.session_factory() as db:
            code = exc.code if isinstance(exc, AppError) else type(exc).__name__
            await fail(
                db, user_id, running.run_id, attempt=running.attempt, code=code, now=rt.now()
            )
            await db.commit()
        return 0
    logger.info("Reading stack: user %s, run %s, %d added", user_id, running.run_id, added)
    return added


async def run_reading_stack(rt: ResearchRuntime, now: datetime) -> int:
    async with rt.session_factory() as db:
        users = await scheduled_user_ids(db)
    return sum([await _run_user(rt, user_id, now) for user_id in users])
