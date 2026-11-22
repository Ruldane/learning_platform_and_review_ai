from typing import Annotated

from fastapi import APIRouter, Query

from app.core.field_paths import FieldPathsRoute
from app.features.ide.router_deps import Id, Ide
from app.features.ide.schemas import RunProgress
from app.features.ide.schemas_notebook import NotebookPut, NotebookRunIn, NotebookView
from app.features.ide.schemas_terminal import TerminalStarted
from app.providers.sandbox.base import MAX_OUTPUT_BYTES, MAX_PATH_CHARS

router = APIRouter(route_class=FieldPathsRoute)
NotebookQuery = Annotated[str, Query(min_length=1, max_length=MAX_PATH_CHARS)]
Offset = Annotated[int, Query(ge=0, le=MAX_OUTPUT_BYTES)]


@router.get("/sessions/{session_id}/notebook")
async def get_notebook(session_id: Id, path: NotebookQuery, ide: Ide) -> NotebookView:
    return await ide.get_notebook(session_id, path)


@router.put("/sessions/{session_id}/notebook")
async def save_notebook(session_id: Id, body: NotebookPut, ide: Ide) -> NotebookView:
    return await ide.save_notebook(session_id, body)


@router.post("/sessions/{session_id}/notebook/run", status_code=202)
async def run_notebook_cell(session_id: Id, body: NotebookRunIn, ide: Ide) -> TerminalStarted:
    return await ide.run_notebook_cell(session_id, body)


@router.get("/notebook-runs/{run_id}")
async def read_notebook_run(run_id: Id, ide: Ide, after: Offset = 0) -> RunProgress:
    return await ide.read_notebook_run(run_id, after)
