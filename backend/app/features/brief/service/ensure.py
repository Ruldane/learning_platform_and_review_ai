"""Create the brief for the local day (P11, P12, D162), on opening (`GET /brief/today`) or at the
set time (morning job): never two briefs for the same day, never two sessions.

Under the user's lock: the day is January's (`brief_day`, never `now.date()`), an existing brief
is returned as is; otherwise the code sections are computed and inserted by
`INSERT … ON CONFLICT DO NOTHING` (unique `(user_id, day)`). **Only the inserter launches** the
`daily_brief` session (subject `brief`) and sets `session_id`; a refused launch (no engine,
session impossible) leaves the advice `unavailable` (final for the day) and the code sections
intact. Nothing waits for an agent: the session runs in the background. Logs: ids and codes;
never a section."""

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
    """`(id of the day's brief, created?)`. Losing the race against another inserter (another
    process) returns the other one's brief, `created` false."""
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
    if rival is None:  # impossible: the conflict comes from a row for this day
        raise brief_not_found()
    return rival.id, False


async def _launch(rt: BriefRuntime, user_id: str, brief_id: str) -> None:
    """Launch the advice session and attach it to the brief; a refusal makes the advice
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
        logger.warning("Brief without a session: brief %s, cause %s", brief_id, safe_code(code))
        return
    async with rt.session_factory() as db:
        await BriefRepository(db, user_id).set_session(brief_id, session_id)
        await db.commit()
    logger.info("Brief launched: user %s, brief %s, session %s", user_id, brief_id, session_id)


async def ensure_today(
    rt: BriefRuntime, user_id: str, *, origin: BriefOrigin, now: datetime | None = None
) -> tuple[BriefOut, bool]:
    """The user's brief for her local day (created if missing) and `created?`. `now`: the moment
    of the scheduled job; without it, the runtime clock."""
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
        "Daily brief: brief %s, created %s, origin %s",
        brief_id,
        created,
        origin,
    )
    return out, created
