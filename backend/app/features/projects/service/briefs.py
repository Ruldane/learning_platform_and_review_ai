"""Mini project briefs (P1, D166): one project per non-skipped module of a validated program,
created once the module's week has started (local Monday ≤ today), by the scheduled job
`project_briefs` (`app.scheduler`, never imported here: contract 8), every 15 minutes and at
startup. A pass only creates (and so only launches) `MAX_NEW_PER_PASS` projects per account,
oldest weeks first: on a program already under way, briefs go out three by three, every
15 minutes, instead of a wall of calls at the same instant (D173).

Reading the validated programs of all accounts (`list_validated_programs`, D91) is the only
read without `user_id`; everything else is done account by account. Creation is guarded in
SQL (`ON CONFLICT (user_id, module_id) DO NOTHING`): **only the inserter launches** the
`project_brief` session, so two passes make only one project and one session. Each pass also
fixes projects whose session died (`settle_all`) and restarts a brief that did not succeed,
three attempts at most, then `brief_failed` ("Retry": `POST /projects/{id}/brief`).
A failure for one account does not stop the others. Logs: identifiers and numbers."""

import logging
from datetime import date, datetime

from app.core.clock import local_today, user_zone
from app.features.program.service.programs import list_validated_programs, load
from app.features.projects.repository import ProjectRepository
from app.features.projects.schemas import SessionStarted
from app.features.projects.service.errors import (
    brief_not_failed,
    brief_unavailable,
    project_not_found,
)
from app.features.projects.service.launch import start_brief_session
from app.features.projects.service.rules import week_started
from app.features.projects.service.runtime import ProjectsRuntime
from app.features.projects.service.settle import settle_all
from app.features.settings.service import SettingsService

logger = logging.getLogger(__name__)

MAX_NEW_PER_PASS = 3


async def _create_missing(
    rt: ProjectsRuntime, user_id: str, programs: list[str], now: datetime
) -> list[str]:
    """The projects created (ids) for non-skipped modules whose week has started."""
    created: list[str] = []
    async with rt.session_factory() as db:
        zone = user_zone((await SettingsService(db, user_id).get()).timezone)
        today = local_today(zone, now)
        repo = ProjectRepository(db, user_id)
        known = await repo.module_ids()
        due: list[tuple[date, str, str, str]] = []  # (week start, program, module, title)
        for program_id in programs:
            loaded = await load(db, user_id, program_id)
            starts = {week.id: week.start_date for week in loaded.weeks}
            for module in loaded.modules:
                start = starts.get(module.week_id)
                if module.skipped or module.id in known or start is None:
                    continue
                if week_started(start, today):
                    due.append((start, program_id, module.id, module.title))
        for _, program_id, module_id, title in sorted(due)[:MAX_NEW_PER_PASS]:
            project_id = await repo.insert_if_absent(
                module_id=module_id, program_id=program_id, title=title, now=now
            )
            if project_id is not None:
                created.append(project_id)
        await db.commit()
    return created


async def _ensure_user(
    rt: ProjectsRuntime, user_id: str, programs: list[str], now: datetime
) -> int:
    async with rt.ensure_lock(user_id):
        created = await _create_missing(rt, user_id, programs, now)
        for project_id in created:
            async with rt.project_lock(user_id, project_id):
                await start_brief_session(rt, user_id, project_id)
        await settle_all(rt, user_id, retry=True)
    return len(created)


async def ensure_project_briefs(rt: ProjectsRuntime, now: datetime) -> int:
    """One pass of the scheduled job; returns the number of projects created (one brief launched
    each)."""
    async with rt.session_factory() as db:
        pairs = await list_validated_programs(db)
    by_user: dict[str, list[str]] = {}
    for user_id, program_id in pairs:
        by_user.setdefault(user_id, []).append(program_id)
    created = 0
    for user_id, programs in by_user.items():
        try:
            created += await _ensure_user(rt, user_id, programs, now)
        except Exception as exc:
            logger.warning("Briefs: user %s not processed (%s)", user_id, type(exc).__name__)
    level = logging.INFO if created else logging.DEBUG
    logger.log(level, "Briefs: %d account(s), %d project(s) created", len(by_user), created)
    return created


async def retry_brief(rt: ProjectsRuntime, user_id: str, project_id: str) -> SessionStarted:
    """Retry: a failed brief starts again for three more attempts; 409
    `brief_not_failed` otherwise, 503 if the engine refuses the launch (the project stays
    failed)."""
    async with rt.project_lock(user_id, project_id):
        async with rt.session_factory() as db:
            row = await ProjectRepository(db, user_id).get_fresh(project_id)
            if row is None:
                raise project_not_found()
            if row.status != "brief_failed":
                raise brief_not_failed()
            row.status, row.brief_attempts, row.session_id = "brief_pending", 1, None
            await db.commit()
        session_id = await start_brief_session(rt, user_id, project_id)
        if session_id is None:
            async with rt.session_factory() as db:
                row = await ProjectRepository(db, user_id).get_fresh(project_id)
                if row is not None:
                    row.status = "brief_failed"
                    await db.commit()
            raise brief_unavailable()
    return SessionStarted(session_id=session_id)
