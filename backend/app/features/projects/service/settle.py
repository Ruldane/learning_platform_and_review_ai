"""A project's status follows its session (D129 no. 5, D166). A `reviewing` or `brief_pending`
project whose session is no longer open (flow failed or cancelled, restart without resume,
interrupted launch) is corrected, **under the project's lock** and on every read, at startup
and on each pass of the statements task:

- `reviewing` without a session: back to `to_redo` (an evaluation already exists) or `todo`;
  nothing was stored (the port only writes a complete evaluation), January can submit again;
- `brief_pending` without a session: `brief_failed` after `BRIEF_ATTEMPTS` tries or if January
  cancelled the flow; otherwise the statements task (`retry`) relaunches a try.

The sessions are read before the row, under the same lock as the launch: a session set
meanwhile never passes for dead. Logs: ids and numbers."""

import logging
from datetime import timedelta

from app.features.projects.repository import ProjectRepository
from app.features.projects.service.launch import start_brief_session
from app.features.projects.service.runtime import (
    BRIEF_ATTEMPTS,
    BRIEF_GRAPH,
    REVIEW_GRAPH,
    SUBJECT,
    ProjectsRuntime,
)
from app.features.sessions.service import list_open_sessions_by_subject, session_facts

logger = logging.getLogger(__name__)

LIVE = ("brief_pending", "reviewing")  # statuses that have a session to follow
# Time to launch the session after the submission or the creation: without a session beyond
# that, the launch was interrupted (process stop).
LAUNCH_GRACE = timedelta(minutes=5)


async def settle_project(
    rt: ProjectsRuntime, user_id: str, project_id: str, *, retry: bool = False
) -> None:
    """Corrects the project if its session is dead. `retry` (statements task only): a statement
    without a session and under the tries limit is relaunched."""
    async with rt.project_lock(user_id, project_id), rt.session_factory() as db:
        repo = ProjectRepository(db, user_id)
        first = await repo.get_fresh(project_id)
        if first is None or first.status not in LIVE:
            return
        graph = REVIEW_GRAPH if first.status == "reviewing" else BRIEF_GRAPH
        open_ids = await list_open_sessions_by_subject(
            db, user_id, graph=graph, subject_type=SUBJECT
        )
        row = await repo.get_fresh(project_id) or first
        if row.session_id is None:
            dead = rt.now() - row.updated_at > LAUNCH_GRACE
        else:
            dead = row.session_id not in open_ids.get(project_id, [])
        if not dead:
            return
        facts = await session_facts(db, user_id, row.session_id) if row.session_id else None
        cancelled = facts is not None and facts.status == "cancelled"
        if row.status == "reviewing":
            row.status = "to_redo" if row.evaluation else "todo"
            row.session_id = None
        elif cancelled or row.brief_attempts >= BRIEF_ATTEMPTS:
            row.status, row.session_id = "brief_failed", None
        elif retry:
            row.brief_attempts += 1
            row.session_id = None
        else:
            return
        await db.commit()
        logger.info("Project without a session: project %s, status %s", project_id, row.status)
        if row.status == "brief_pending":
            await start_brief_session(rt, user_id, project_id)


async def settle_all(rt: ProjectsRuntime, user_id: str, *, retry: bool = False) -> None:
    """Corrects the user's projects in progress (before any read of a status)."""
    async with rt.session_factory() as db:
        ids = [row.id for row in await ProjectRepository(db, user_id).in_status(LIVE)]
    for project_id in ids:
        await settle_project(rt, user_id, project_id, retry=retry)
