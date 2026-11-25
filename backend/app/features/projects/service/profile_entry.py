"""The entry of a validated project into the master profile (rule 5, P3, D166): `POST
/projects/{id}/profile-entry`, **the only path**. "Nothing enters the master profile without
validation": neither the project's validation, nor the Practitioner, nor a draft writes to the
profile; January clicks, with her text (the draft's, possibly edited).

Under the project's lock: 409 `project_not_validated`, `entry_already_added` (`profile_version`
already set: a double click does not add it twice), `profile_required` (no validated profile),
`profile_draft_pending` (a more recent draft is waiting for January: the new version would bury
it), `profile_projects_full` (20 projects). Otherwise a new version **validated** by
`save_profile` (source `january`) with the project added (repository link if it fits in 300
characters, source `january`); `profile_version` is set. Logs: ids and version numbers."""

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
    """Sets `profile_version` on the project **in the transaction** of the new profile version:
    both together or neither, a stop between the two never leaves the project in the profile
    without the project knowing it (a new click would not add it twice)."""

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
            logger.info("Project added to the profile: project %s, version %d", project_id, version)
            return await project_out_live(db, user_id, row)
