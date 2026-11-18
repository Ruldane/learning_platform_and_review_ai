"""Relancer les brouillons d'un projet validé qui n'en a pas (D173 n° 4, D181) :
`POST /projects/{id}/drafts`, sous le verrou du projet. Leur écriture avait échoué (« brouillons
indisponibles ») : une session `project_review` en mode `drafts` les écrit, **sans refaire
l'évaluation** (un appel standard, un nouvel essai au plus, `text_claims` comme à la validation).

Refus : projet d'une autre (404), pas validé (409 `project_not_validated`), brouillons déjà là (409
`drafts_present`), session des brouillons ou de l'évaluation encore ouverte (409
`review_in_progress`, `details.session_id`), lancement refusé (503 `drafts_unavailable`, rien n'est
changé). Journaux : identifiants et codes seulement."""

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
    """Le projet peut recevoir ses brouillons ; sinon l'erreur lisible. Rend sa dernière session,
    dont la relance reprend la source (client joué ou fournisseur forcé)."""
    async with rt.session_factory() as db:
        row = await owned(db, user_id, project_id)
        open_ids = await list_open_sessions_by_subject(
            db, user_id, graph=REVIEW_GRAPH, subject_type=SUBJECT
        )
        running = open_ids.get(project_id, [])
        if row.status == "reviewing":
            raise review_in_progress(running[0] if running else row.session_id)
        if running:  # le projet est validé : c'est la session des brouillons qui tourne
            raise review_in_progress(running[0], "Les brouillons s'écrivent déjà.")
        if row.status != "validated":
            raise project_not_validated("Seul un projet validé a des brouillons.")
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
            logger.warning(
                "Brouillons non lancés : projet %s, cause %s", project_id, safe_code(code)
            )
            raise drafts_unavailable() from None
        async with rt.session_factory() as db:
            row = await owned(db, user_id, project_id)
            row.session_id = session_id
            await db.commit()
    logger.info("Brouillons relancés : projet %s, session %s", project_id, session_id)
    return SessionStarted(session_id=session_id)
