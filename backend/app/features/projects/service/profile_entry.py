"""L'entrée d'un projet validé dans le profil maître (rule 5, P3, D166) : `POST
/projects/{id}/profile-entry`, **le seul chemin**. « Rien n'entre dans le profil maître sans
validation » : ni la validation du projet, ni le Praticien, ni un brouillon n'écrivent au profil ;
January clique, avec son texte (celui du brouillon, éventuellement modifié).

Sous le verrou du projet : 409 `project_not_validated`, `entry_already_added` (`profile_version`
déjà posé : un double clic ne l'ajoute pas deux fois), `profile_required` (aucun profil validé),
`profile_draft_pending` (un brouillon plus récent attend January : la nouvelle version
l'enterrerait), `profile_projects_full` (20 projets). Sinon une nouvelle version **validée** par
`save_profile` (source `january`) avec le projet ajouté (lien du dépôt s'il tient en 300 caractères,
source `january`) ; `profile_version` est posé. Journaux : identifiants et numéros de version."""

import logging
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.cv_schema import Line, Project, assign_fact_ids
from app.features.cv.service.profile import profile_state, save_profile_data
from app.features.cv.service.profile_facts import profile_draft_pending
from app.features.projects.schemas import ProfileEntryIn, ProjectOut
from app.features.projects.service.errors import (
    entry_already_added,
    profile_projects_full,
    profile_required,
    project_not_validated,
)
from app.features.projects.service.inputs import latest_submission, owned
from app.features.projects.service.runtime import ProjectsRuntime
from app.features.projects.service.views import project_out_live

logger = logging.getLogger(__name__)

LINK_MAX = 300  # `Project.link`
PROJECTS_MAX = 20  # `MasterProfileData.projects`


def _recorder(user_id: str, project_id: str) -> Callable[[AsyncSession, int], Awaitable[None]]:
    """Pose `profile_version` sur le projet **dans la transaction** de la nouvelle version du
    profil : les deux ensemble ou aucun, un arrêt entre les deux ne laisse jamais le projet dans le
    profil sans que le projet le sache (un nouveau clic ne l'ajouterait pas deux fois)."""

    async def record(db: AsyncSession, version: int) -> None:
        row = await owned(db, user_id, project_id)
        row.profile_version = version
        await db.flush()

    return record


async def add_profile_entry(
    rt: ProjectsRuntime, user_id: str, project_id: str, body: ProfileEntryIn
) -> ProjectOut:
    async with rt.project_lock(user_id, project_id):
        async with rt.session_factory() as db:
            row = await owned(db, user_id, project_id)
            if row.status != "validated":
                raise project_not_validated()
            if row.profile_version is not None:
                raise entry_already_added()
            state = await profile_state(db, user_id)
            link = latest_submission(row).get("repo_url")
        if state.validated is None:
            raise profile_required()
        if state.draft is not None:
            raise profile_draft_pending()
        profile = state.validated.data
        if len(profile.projects) >= PROJECTS_MAX:
            raise profile_projects_full()
        entry = Project(
            name=body.name,
            description=body.description,
            link=link if isinstance(link, str) and len(link) <= LINK_MAX else None,
            achievements=[Line(text=text) for text in body.achievements],
            sources=["january"],
        )
        data = assign_fact_ids(profile.model_copy(update={"projects": [*profile.projects, entry]}))
        version = await save_profile_data(
            rt.cv,
            user_id,
            data,
            state.validated.version,
            in_transaction=_recorder(user_id, project_id),
        )
        async with rt.session_factory() as db:
            row = await owned(db, user_id, project_id)
            logger.info("Projet ajouté au profil : projet %s, version %d", project_id, version)
            return await project_out_live(db, user_id, row)
