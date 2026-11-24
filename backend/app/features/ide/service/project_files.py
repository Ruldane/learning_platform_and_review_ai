"""Targeted writes on a Python session's files, without access to the host disk."""

from app.core.errors import AppError
from app.db.base import utcnow
from app.db.models.ide import IdeSession
from app.features.ide.repository import PreferenceRepository
from app.features.ide.service import project_tabs, sessions
from app.features.ide.service.context import IdeContext
from app.features.ide.service.errors import mcp_ide_test_file, mcp_ide_write_off
from app.providers.sandbox.base import check_file_name

# The launcher checks segment length and depth again when materializing.
_MAX_DEPTH = 8
_MAX_COMPONENT_CHARS = 100
_MAX_COMPONENT_BYTES = 255


def _changed() -> AppError:
    return AppError(
        "project_changed",
        "The project changed. Re-read its files before changing the file tree.",
        409,
    )


def _not_found() -> AppError:
    return AppError("project_file_not_found", "Project file not found.", 404)


def _invalid_path() -> AppError:
    return AppError("project_path_invalid", "This file path is refused by the sandbox.", 422)


def _check_destination(files: dict[str, str], path: str) -> None:
    try:
        check_file_name(path)
        parts = path.split("/")
        if len(parts) > _MAX_DEPTH or any(
            len(part) > _MAX_COMPONENT_CHARS or len(part.encode()) > _MAX_COMPONENT_BYTES
            for part in parts
        ):
            raise _invalid_path()
    except ValueError:
        raise _invalid_path() from None
    if path in files:
        raise AppError("project_file_exists", "A file already has this name.", 409)
    if any(name.startswith(path + "/") or path.startswith(name + "/") for name in files):
        raise AppError("project_path_conflict", "A file and a folder use the same path.", 409)


async def _edit_session(ctx: IdeContext, session_id: str, version: int, *paths: str) -> IdeSession:
    project = await sessions.get(ctx, session_id)
    if ctx.caller.kind == "mcp":
        prefs = await PreferenceRepository(ctx.db, ctx.user_id).mine()
        if prefs is None or not prefs.mcp_can_write_files:
            raise mcp_ide_write_off()
        if project.exercise_id is not None and any(sessions.is_test_file(path) for path in paths):
            raise mcp_ide_test_file()
    if version != project.files_version:
        raise _changed()
    return project


def _files(project: IdeSession) -> dict[str, str]:
    return {path: str(content) for path, content in project.files.items()}


async def _save(
    ctx: IdeContext,
    project: IdeSession,
    files: dict[str, str],
    entry: str,
    rename: tuple[str, str] | None = None,
) -> IdeSession:
    try:
        sessions.check_files(files, entry)
    except UnicodeEncodeError:
        raise AppError("project_file_encoding", "The file must be valid UTF-8 text.", 422) from None
    if not await sessions.claim_files(ctx, project):
        raise _changed()
    await ctx.db.refresh(project, attribute_names=["workspace_tabs"])
    project.files = files
    project.entry = entry
    if project.workspace_tabs is not None:
        project.workspace_tabs = project_tabs.current(project, rename).to_state().model_dump()
    project.updated_at = utcnow()
    await ctx.db.flush()
    return project


async def create(
    ctx: IdeContext, session_id: str, path: str, content: str, *, version: int
) -> IdeSession:
    project = await _edit_session(ctx, session_id, version, path)
    files = _files(project)
    _check_destination(files, path)
    files[path] = content
    return await _save(ctx, project, files, project.entry)


async def update(
    ctx: IdeContext, session_id: str, path: str, content: str, *, version: int
) -> IdeSession:
    project = await _edit_session(ctx, session_id, version, path)
    files = _files(project)
    if path not in files:
        raise _not_found()
    files[path] = content
    return await _save(ctx, project, files, project.entry)


async def rename(
    ctx: IdeContext, session_id: str, path: str, destination: str, *, version: int
) -> IdeSession:
    project = await _edit_session(ctx, session_id, version, path, destination)
    files = _files(project)
    if path not in files:
        raise _not_found()
    if path == destination:
        return project
    content = files.pop(path)
    _check_destination(files, destination)
    files[destination] = content
    entry = destination if path == project.entry else project.entry
    return await _save(ctx, project, files, entry, (path, destination))


async def remove(
    ctx: IdeContext,
    session_id: str,
    path: str,
    *,
    version: int,
    replacement_entry: str | None = None,
) -> IdeSession:
    project = await _edit_session(ctx, session_id, version, path)
    files = _files(project)
    if path not in files:
        raise _not_found()
    del files[path]
    return await _save(ctx, project, files, replacement_entry or project.entry)
