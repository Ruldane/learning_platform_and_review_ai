from typing import Annotated

from fastapi import APIRouter, Query, Response

from app.core.field_paths import FieldPathsRoute
from app.features.ide.router_deps import Id, Ide
from app.features.ide.schemas import RunProgress
from app.features.ide.schemas_terminal import TerminalInput, TerminalStarted

router = APIRouter(route_class=FieldPathsRoute)
Offset = Annotated[int, Query(ge=0, le=65_536)]


@router.post("/sessions/{session_id}/terminal", status_code=202)
async def start_terminal(session_id: Id, ide: Ide) -> TerminalStarted:
    return await ide.start_terminal(session_id)


@router.get("/terminals/{run_id}")
async def read_terminal(run_id: Id, ide: Ide, after: Offset = 0) -> RunProgress:
    return await ide.read_terminal(run_id, after)


@router.post("/terminals/{run_id}/input", status_code=204, response_class=Response)
async def send_terminal(run_id: Id, body: TerminalInput, ide: Ide) -> Response:
    await ide.send_terminal(run_id, body.data)
    return Response(status_code=204)


@router.delete("/terminals/{run_id}", status_code=204, response_class=Response)
async def cancel_terminal(run_id: Id, ide: Ide) -> Response:
    await ide.cancel_terminal(run_id)
    return Response(status_code=204)
