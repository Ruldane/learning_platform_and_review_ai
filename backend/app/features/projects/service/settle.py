"""Le statut d'un projet suit sa session (D129 n° 5, D166). Un projet `reviewing` ou
`brief_pending` dont la session n'est plus ouverte (parcours en échec ou annulé, redémarrage sans
reprise, lancement interrompu) est corrigé, **sous le verrou du projet** et à chaque lecture, au
démarrage et à chaque passage de la tâche des énoncés :

- `reviewing` sans session : retour à `to_redo` (une évaluation existe déjà) ou `todo` ; rien n'a
  été rangé (le port n'écrit qu'une évaluation complète), January peut rendre de nouveau ;
- `brief_pending` sans session : `brief_failed` après `BRIEF_ATTEMPTS` essais ou si January a
  annulé le parcours ; sinon la tâche des énoncés (`retry`) relance un essai.

Les sessions sont lues avant la ligne, sous le même verrou que le lancement : une session posée
entre-temps ne passe jamais pour morte. Journaux : identifiants et nombres."""

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

LIVE = ("brief_pending", "reviewing")  # statuts qui ont une session à suivre
# Le temps de lancer la session après le rendu ou la création : sans session au-delà, le
# lancement a été interrompu (arrêt du processus).
LAUNCH_GRACE = timedelta(minutes=5)


async def settle_project(
    rt: ProjectsRuntime, user_id: str, project_id: str, *, retry: bool = False
) -> None:
    """Corrige le projet si sa session est morte. `retry` (tâche des énoncés seulement) : un énoncé
    sans session et sous la limite d'essais est relancé."""
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
        logger.info("Projet sans session : projet %s, statut %s", project_id, row.status)
        if row.status == "brief_pending":
            await start_brief_session(rt, user_id, project_id)


async def settle_all(rt: ProjectsRuntime, user_id: str, *, retry: bool = False) -> None:
    """Corrige les projets en cours de l'utilisatrice (avant toute lecture d'un statut)."""
    async with rt.session_factory() as db:
        ids = [row.id for row in await ProjectRepository(db, user_id).in_status(LIVE)]
    for project_id in ids:
        await settle_project(rt, user_id, project_id, retry=retry)
