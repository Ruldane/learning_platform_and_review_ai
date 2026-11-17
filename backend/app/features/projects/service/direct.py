"""L'énoncé d'un mini projet écrit en direct (phase 10, 10.W) : January ou Claude (par le MCP)
fournit l'énoncé, l'application le range comme le fait le port du Praticien (`save_brief`), sans
agent ni session : le projet passe à « à faire » et prend le titre de l'énoncé. Le rendu et son
évaluation restent ceux de l'application (ils lancent un agent : ce n'est pas écrit ici).

Un projet par module (index unique) ; l'énoncé ne se retouche que tant que rien n'est rendu."""

import logging

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.features.program.service.programs import load, program_of_module
from app.features.projects.repository import ProjectRepository
from app.features.projects.schemas import (
    ProjectBriefIn,
    ProjectBriefPatch,
    ProjectCreateIn,
    ProjectOut,
)
from app.features.projects.service.errors import (
    invalid_submission,
    module_skipped,
    project_exists,
    project_not_editable,
)
from app.features.projects.service.inputs import owned
from app.features.projects.service.runtime import ProjectsRuntime
from app.features.projects.service.views import project_out_live

logger = logging.getLogger(__name__)

EDITABLE = ("brief_pending", "brief_failed", "todo")  # sans rendu : l'énoncé peut encore changer


async def create_project(rt: ProjectsRuntime, user_id: str, body: ProjectCreateIn) -> ProjectOut:
    """Le projet du module, à faire, avec l'énoncé donné ; 404 `module_not_found`, 409
    `project_exists` ou `module_skipped`."""
    async with rt.session_factory() as db:
        program_id = await program_of_module(db, user_id, body.module_id)
    async with rt.ensure_lock(user_id), rt.session_factory() as db:
        loaded = await load(db, user_id, program_id)
        module = next(m for m in loaded.modules if m.id == body.module_id)
        if module.skipped:
            raise module_skipped()
        repo = ProjectRepository(db, user_id)
        if body.module_id in await repo.module_ids():
            raise project_exists()
        try:
            project = await repo.add(
                module_id=body.module_id,
                program_id=program_id,
                title=body.brief.title,
                brief=body.brief.model_dump(mode="json"),
                status="todo",
                brief_attempts=0,
                submissions=[],
                drafts={},
            )
            await db.commit()
        except IntegrityError:  # une autre requête vient de le créer
            await db.rollback()
            raise project_exists() from None
        project_id = project.id
    logger.info("Projet écrit en direct : module %s, projet %s", body.module_id, project_id)
    async with rt.session_factory() as db:
        return await project_out_live(db, user_id, (await owned(db, user_id, project_id)))


def _merged(current: dict[str, object] | None, patch: ProjectBriefPatch) -> ProjectBriefIn:
    """L'énoncé retouché, revalidé en entier ; 422 `fields` si un champ manque (projet sans
    énoncé) ou ne tient pas les bornes."""
    given = patch.model_dump(exclude_none=True)
    try:
        return ProjectBriefIn.model_validate({**(current or {}), **given})
    except ValidationError as exc:
        fields = sorted({str(error["loc"][0]) for error in exc.errors() if error["loc"]})
        raise invalid_submission(fields) from None


async def patch_project(
    rt: ProjectsRuntime, user_id: str, project_id: str, patch: ProjectBriefPatch
) -> ProjectOut:
    """Retouche l'énoncé d'un projet qui n'a pas de rendu (409 `project_not_editable` sinon) ; un
    projet dont l'énoncé n'est pas écrit le reçoit en entier."""
    async with rt.project_lock(user_id, project_id), rt.session_factory() as db:
        row = await owned(db, user_id, project_id)
        if row.status not in EDITABLE:
            raise project_not_editable()
        brief = _merged(row.brief, patch)
        row.brief = brief.model_dump(mode="json")
        row.title = brief.title[:200]
        row.status, row.session_id = "todo", None
        await db.commit()
    logger.info("Énoncé retouché en direct : projet %s", project_id)
    async with rt.session_factory() as db:
        return await project_out_live(db, user_id, (await owned(db, user_id, project_id)))
