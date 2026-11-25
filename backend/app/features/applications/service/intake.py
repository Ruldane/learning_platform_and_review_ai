"""Launching the creation of a record from one sentence (`application_intake` flow, D141), under
a user lock: a single intake session open at a time (409 `intake_in_progress`,
`details.session_id`: the one that is waiting). The sentence is never logged (17.2): ids
only."""

import logging

from app.core.errors import AppError
from app.features.applications.service.runtime import ApplicationsRuntime
from app.features.sessions.service import find_active_session

logger = logging.getLogger(__name__)

GRAPH = "application_intake"
SUBJECT = "application_intake"
LOCK_KEY = "intake"


def intake_in_progress(session_id: str) -> AppError:
    return AppError(
        "intake_in_progress",
        "Confirm or cancel the application already in progress before starting another one.",
        409,
        {"session_id": session_id},
    )


async def start_intake(rt: ApplicationsRuntime, user_id: str, text: str) -> str:
    """Launches the tracking assistant on the sentence and returns the session id."""
    async with rt.locks.get(user_id, LOCK_KEY):
        async with rt.session_factory() as db:
            open_id = await find_active_session(
                db, user_id, graph=GRAPH, subject_type=SUBJECT, subject_id=user_id
            )
        if open_id is not None:
            raise intake_in_progress(open_id)
        session_id = await rt.launcher.start(
            user_id, GRAPH, {"text": text}, subject_type=SUBJECT, subject_id=user_id
        )
    logger.info("One-sentence creation started: user %s, session %s", user_id, session_id)
    return session_id
