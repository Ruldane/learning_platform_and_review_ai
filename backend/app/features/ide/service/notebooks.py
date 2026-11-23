"""Édition du fichier `.ipynb` et stockage tardif du résultat de la bonne cellule."""

from sqlalchemy import update

from app.core.errors import AppError
from app.db.models.ide import IdeRun, IdeSession
from app.features.ide.notebook_format import Notebook
from app.features.ide.repository import RunRepository
from app.features.ide.schemas import RunProgress
from app.features.ide.schemas_notebook import NotebookPut, NotebookRunIn, NotebookView
from app.features.ide.schemas_terminal import TerminalStarted
from app.features.ide.service import project_files, runs, sessions
from app.features.ide.service.context import IdeContext, file_hash
from app.providers.sandbox.base import check_file_name


def _path(path: str) -> None:
    try:
        check_file_name(path)
        if path.casefold().endswith(".ipynb"):
            return
    except ValueError:
        pass
    raise AppError("notebook_path_invalid", "Choisis un chemin de fichier .ipynb valide.", 422)


def _read(project: IdeSession, path: str) -> Notebook:
    if path not in project.files:
        raise AppError("notebook_not_found", "Notebook introuvable.", 404)
    return Notebook.parse(str(project.files[path]))


async def get(ctx: IdeContext, session_id: str, path: str) -> NotebookView:
    project = await sessions.get(ctx, session_id)
    _path(path)
    book = _read(project, path)
    active = await RunRepository(ctx.db, ctx.user_id).pending_notebook(session_id, path)
    if active is None:
        return NotebookView(path=path, cells=book.cells(), files_version=project.files_version)
    try:
        result = await progress(ctx, active.id, 0)
    except AppError as exc:
        if exc.code != "sandbox_unavailable":
            raise
        return NotebookView(path=path, cells=book.cells(), files_version=project.files_version)
    if ctx.caller.kind == "app" and result.status != "running":
        project = await sessions.get(ctx, session_id)
        book = _read(project, path)
    return NotebookView(
        path=path,
        cells=book.cells(),
        files_version=project.files_version,
        active_run_id=active.id if result.status == "running" else None,
    )


async def save(ctx: IdeContext, session_id: str, draft: NotebookPut) -> NotebookView:
    project = await sessions.get(ctx, session_id)
    _path(draft.path)
    book = Notebook.parse(str(project.files.get(draft.path, "")))
    book.replace(draft.cells)
    edit = project_files.update if draft.path in project.files else project_files.create
    saved = await edit(ctx, session_id, draft.path, book.to_json(), version=draft.version)
    return NotebookView(path=draft.path, cells=book.cells(), files_version=saved.files_version)


async def start(ctx: IdeContext, session_id: str, draft: NotebookRunIn) -> TerminalStarted:
    project = await sessions.get(ctx, session_id)
    _path(draft.path)
    book = _read(project, draft.path)
    source = book.source(draft.cell_id, include_previous=draft.include_previous)
    run = await runs.start(
        ctx,
        session_id,
        "notebook",
        None,
        source=source,
        notebook_cell={
            **draft.model_dump(),
            "source_hash": file_hash(source),
        },
    )
    return TerminalStarted(id=run.id)


async def _claim_result(ctx: IdeContext, row: IdeRun, cell_id: str) -> bool:
    stmt = (
        update(IdeRun)
        .where(
            IdeRun.user_id == ctx.user_id,
            IdeRun.id == row.id,
            IdeRun.notebook_cell["cell_id"].as_string() == cell_id,
        )
        .values(notebook_cell=None)
        .returning(IdeRun.id)
    )
    return (await ctx.db.execute(stmt)).scalar_one_or_none() is not None


async def _store_output(ctx: IdeContext, run_id: str) -> None:
    row = await RunRepository(ctx.db, ctx.user_id).get_fresh(run_id)
    if row is None or row.notebook_cell is None:
        return
    info = dict(row.notebook_cell)
    draft = NotebookRunIn.model_validate(info)
    if not await _claim_result(ctx, row, draft.cell_id):
        return
    try:
        project = await sessions.get(ctx, row.session_id)
        book = _read(project, draft.path)
        source = book.source(draft.cell_id, include_previous=draft.include_previous)
        if file_hash(source) != info["source_hash"]:
            return
        book.record_output(draft.cell_id, row.output)
        await project_files.update(
            ctx,
            project.id,
            draft.path,
            book.to_json(),
            version=project.files_version,
        )
    except AppError as exc:
        if exc.code not in {
            "session_not_found",
            "notebook_not_found",
            "cell_not_found",
            "notebook_invalid",
            "project_changed",
            "files_too_large",
        }:
            raise


async def progress(ctx: IdeContext, run_id: str, after: int) -> RunProgress:
    persist = ctx.caller.kind == "app"
    result = await runs.progress(ctx, run_id, after, kind="notebook", persist=persist)
    if persist and result.status != "running":
        await _store_output(ctx, run_id)
    return result
