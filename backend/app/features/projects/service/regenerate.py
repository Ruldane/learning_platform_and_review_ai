"""Relaunching the drafts of a validated project that has none (D173 no. 4, D181):
`POST /projects/{id}/drafts`, under the project's lock. Their writing had failed ("drafts
unavailable"): a `project_review` session in `drafts` mode writes them, **without redoing the
evaluation** (one standard call, one retry at most, `text_claims` as at validation).

Refusals: another user's project (404), not validated (409 `project_not_validated`), drafts
already there (409 `drafts_present`), drafts or evaluation session still open (409
`review_in_progress`, `details.session_id`), launch refused (503 `drafts_unavailable`, nothing
is changed). Logs: ids and codes only."""

import logging

from app.core.errors import AppError
from app.core.played import inherit_source
from app.features.ledger.service.ledger import safe_code
from app.features.projects.schemas import SessionStarted
from app.features.projects.service.errors import (
    drafts_present,
    drafts_unavailable,
    project_not_validated,
    review_in_progress,
)
from app.features.projects.service.inputs import owned
from app.features.projects.service.runtime import REVIEW_GRAPH, SUBJECT, ProjectsRuntime
from app.features.projects.service.settle import settle_project
from app.features.sessions.service import (
    SessionFacts,
    list_open_sessions_by_subject,
    session_facts,
)

logger = logging.getLogger(__name__)


async def _check(rt: ProjectsRuntime, user_id: str, project_id: str) -> SessionFacts | None:
    """The project can receive its drafts; otherwise the readable error. Returns its last
    session, whose relaunch takes over the source (played client or forced provider)."""
    async with rt.session_factory() as db:
        row = await owned(db, user_id, project_id)
        open_ids = await list_open_sessions_by_subject(
            db, user_id, graph=REVIEW_GRAPH, subject_type=SUBJECT
        )
        running = open_ids.get(project_id, [])
        if row.status == "reviewing":
            raise review_in_progress(running[0] if running else row.session_id)
        if running:  # the project is validated: it is the drafts session that is running
            raise review_in_progress(running[0], "The drafts are already being written.")
        if row.status != "validated":
            raise project_not_validated("Only a validated project has drafts.")
        if row.drafts:
            raise drafts_present()
        return await session_facts(db, user_id, row.session_id) if row.session_id else None


async def regenerate_drafts(rt: ProjectsRuntime, user_id: str, project_id: str) -> SessionStarted:
    await settle_project(rt, user_id, project_id)
    async with rt.project_lock(user_id, project_id):
        source = await _check(rt, user_id, project_id)
        try:
            with inherit_source(
                user_id,
                source.played_by if source else None,
                source.model_provider if source else None,
                has_origin=source is not None,
            ):
                session_id = await rt.launcher.start(
                    user_id,
                    REVIEW_GRAPH,
                    {"project_id": project_id, "mode": "drafts"},
                    subject_type=SUBJECT,
                    subject_id=project_id,
                )
        except Exception as exc:
            code = exc.code if isinstance(exc, AppError) else type(exc).__name__
            logger.warning("Drafts not started: project %s, cause %s", project_id, safe_code(code))
            raise drafts_unavailable() from None
        async with rt.session_factory() as db:
            row = await owned(db, user_id, project_id)
            row.session_id = session_id
            await db.commit()
    logger.info("Drafts relaunched: project %s, session %s", project_id, session_id)
    return SessionStarted(session_id=session_id)
