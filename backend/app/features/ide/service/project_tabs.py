"""Vue de projet à restaurer après une réouverture ou une modification des fichiers."""

from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy import update

from app.core.errors import AppError
from app.db.models.ide import IdeSession
from app.features.ide.schemas_project import ProjectTabsState
from app.features.ide.service import sessions
from app.features.ide.service.context import IdeContext


@dataclass(frozen=True)
class ProjectTabs:
    open_paths: tuple[str, ...]
    active_path: str | None

    def renamed(self, source: str, destination: str) -> "ProjectTabs":
        """La position et la sélection d'un fichier suivent son nouveau chemin."""
        return ProjectTabs(
            tuple(destination if path == source else path for path in self.open_paths),
            destination if self.active_path == source else self.active_path,
        )

    def to_state(self) -> ProjectTabsState:
        return ProjectTabsState(open_paths=list(self.open_paths), active_path=self.active_path)


def _stored(raw: Mapping[str, object] | None) -> ProjectTabs | None:
    if not raw:
        return None
    paths, active = raw.get("open_paths"), raw.get("active_path")
    if not isinstance(paths, list):
        return None
    return ProjectTabs(
        tuple(path for path in paths if isinstance(path, str)),
        active if isinstance(active, str) else None,
    )


def restore(files: Mapping[str, object], entry: str, saved: ProjectTabs | None) -> ProjectTabs:
    if saved is not None:
        keep = tuple(dict.fromkeys(path for path in saved.open_paths if path in files))
        if keep:
            return ProjectTabs(keep, saved.active_path if saved.active_path in keep else keep[0])
    first = entry if entry in files else min(files, default=None)
    return ProjectTabs((first,) if first is not None else (), first)


def current(project: IdeSession, rename: tuple[str, str] | None = None) -> ProjectTabs:
    saved = _stored(project.workspace_tabs)
    if saved is not None and rename is not None:
        saved = saved.renamed(*rename)
    return restore(project.files, project.entry, saved)


async def save(ctx: IdeContext, session_id: str, draft: ProjectTabsState) -> ProjectTabsState:
    project = await sessions.get(ctx, session_id)
    proposed = ProjectTabs(tuple(draft.open_paths), draft.active_path)
    state = restore(project.files, project.entry, proposed).to_state()
    stmt = (
        update(IdeSession)
        .where(
            IdeSession.user_id == ctx.user_id,
            IdeSession.id == session_id,
            IdeSession.files_version == project.files_version,
        )
        .values(workspace_tabs=state.model_dump(), updated_at=IdeSession.updated_at)
        .returning(IdeSession.id)
    )
    if (await ctx.db.execute(stmt)).scalar_one_or_none() is None:
        raise AppError("project_changed", "Le projet a changé. Relis les onglets.", 409)
    return state
