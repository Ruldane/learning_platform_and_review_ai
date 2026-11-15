"""Lancement de la création d'une fiche en une phrase (parcours `application_intake`, D141), sous
un verrou de l'utilisatrice : une seule session d'intake ouverte à la fois (409
`intake_in_progress`, `details.session_id` : celle qui attend). La phrase n'est jamais
journalisée (17.2) : identifiants seulement."""

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
        "Une fiche est déjà en préparation : confirme-la ou annule-la d'abord.",
        409,
        {"session_id": session_id},
    )


async def start_intake(rt: ApplicationsRuntime, user_id: str, text: str) -> str:
    """Lance l'Assistant de suivi sur la phrase et rend l'identifiant de la session."""
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
    logger.info("Création en une phrase lancée : utilisateur %s, session %s", user_id, session_id)
    return session_id
