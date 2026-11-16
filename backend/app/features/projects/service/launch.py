"""Lancer la session de l'énoncé d'un projet (P1) et la poser sur la ligne. Aucun verrou ici :
l'appelant tient `project_lock` (ou le projet vient d'être créé, personne d'autre ne le connaît).
Journaux : identifiants et codes seulement."""

import logging

from app.core.errors import AppError
from app.features.ledger.service.ledger import safe_code
from app.features.projects.repository import ProjectRepository
from app.features.projects.service.runtime import BRIEF_GRAPH, SUBJECT, ProjectsRuntime

logger = logging.getLogger(__name__)


async def start_brief_session(rt: ProjectsRuntime, user_id: str, project_id: str) -> str | None:
    """Lance `project_brief` sur le projet ; rend la session posée, `None` si le lancement a été
    refusé (moteur absent…) : le projet reste `brief_pending` sans session, la tâche
    suivante réessaie dans la limite des essais."""
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
        logger.warning("Énoncé non lancé : projet %s, cause %s", project_id, safe_code(code))
        return None
    async with rt.session_factory() as db:
        row = await ProjectRepository(db, user_id).get_fresh(project_id)
        if row is not None:
            row.session_id = session_id
            await db.commit()
    logger.info("Énoncé lancé : projet %s, session %s", project_id, session_id)
    return session_id
