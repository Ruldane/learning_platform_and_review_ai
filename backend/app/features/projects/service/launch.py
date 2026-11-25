"""Launching a project's statement session (P1) and setting it on the row. No lock here: the
caller holds `project_lock` (or the project has just been created, nobody else knows it).
Logs: ids and codes only."""

import logging

from app.core.errors import AppError
from app.features.ledger.service.ledger import safe_code
from app.features.projects.repository import ProjectRepository
from app.features.projects.service.runtime import BRIEF_GRAPH, SUBJECT, ProjectsRuntime

logger = logging.getLogger(__name__)


async def start_brief_session(rt: ProjectsRuntime, user_id: str, project_id: str) -> str | None:
    """Launches `project_brief` on the project; returns the session set, `None` if the launch was
    refused (engine missing...): the project stays `brief_pending` without a session, the next
    task retries within the limit of tries."""
    try:
        session_id = await rt.launcher.start(
            user_id,
            BRIEF_GRAPH,
            {"project_id": project_id},
            subject_type=SUBJECT,
            subject_id=project_id,
        )
    except Exception as exc:
        code = exc.code if isinstance(exc, AppError) else type(exc).__name__
        logger.warning("Statement not started: project %s, cause %s", project_id, safe_code(code))
        return None
    async with rt.session_factory() as db:
        row = await ProjectRepository(db, user_id).get_fresh(project_id)
        if row is not None:
            row.session_id = session_id
            await db.commit()
    logger.info("Statement started: project %s, session %s", project_id, session_id)
    return session_id
