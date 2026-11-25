"""MCP access management API (phase 10, P1, P15 to P19): master switch, feature and tool
tables, tokens, "To confirm" requests, call log, changes and undo. Laid down by 10.P (final
surface and schemas); 10.B1 filled in the switch, the tokens and the log, 10.B2 the tool
tables, the "To confirm" requests and the changes. These routes are **the interface's**: the
`mcp` feature is never exposed to MCP (level 4), an MCP token never opens `/api/v1` (refused
here with 403) and `get_interface_user` even refuses a call carried by an MCP identity."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request, Response

from app.core.deps import Db, InterfaceUserDep, get_interface_user
from app.core.field_paths import FieldPathsRoute
from app.features.mcp.schemas import (
    McpActionOut,
    McpCallOut,
    McpChangeOut,
    McpConfirmationOut,
    McpFeatureOut,
    McpSettingsIn,
    McpSettingsOut,
    McpTokenCreated,
    McpTokenCreateIn,
    McpTokenOut,
    McpUndoOut,
)
from app.features.mcp.service import CallsService, PrefsService, TokenService
from app.features.mcp.service.actions import list_actions as table_of_actions
from app.features.mcp.service.actions import list_features as table_of_features
from app.features.mcp.service.changes import ChangesService
from app.features.mcp.service.confirmations import ConfirmationService
from app.features.memory.service.direct import schedule_indexing
from app.mcp.auth import guard_interface_request
from app.mcp.registry import Registry

router = APIRouter(
    prefix="/mcp",
    tags=["mcp"],
    route_class=FieldPathsRoute,
    dependencies=[Depends(guard_interface_request), Depends(get_interface_user)],
)

Id = Annotated[str, Path(min_length=1, max_length=36)]
Limit = Annotated[int, Query(ge=1, le=100)]


def _known_features(request: Request) -> frozenset[str] | None:
    """The features that declare tools (`None` as long as none declares any)."""
    gate = getattr(request.app.state, "mcp_gate", None)
    return gate.known_features if gate is not None else None


@router.get("/settings", response_model=McpSettingsOut)
async def get_settings(current: InterfaceUserDep, db: Db) -> McpSettingsOut:
    """The MCP master switch (off by default)."""
    return await PrefsService(db, current.id).get()


@router.put("/settings", response_model=McpSettingsOut)
async def put_settings(body: McpSettingsIn, current: InterfaceUserDep, db: Db) -> McpSettingsOut:
    """Turns all MCP access on or off in one gesture."""
    return await PrefsService(db, current.id).set_enabled(body.enabled)


def _registry(request: Request) -> Registry:
    registry: Registry = request.app.state.mcp_registry
    return registry


def _confirmations(request: Request, user_id: str) -> ConfirmationService:
    """The service of this account's requests, with the sender that replays a confirmed request."""
    service: ConfirmationService = request.app.state.mcp_confirmations(user_id)
    return service


@router.get("/features", response_model=list[McpFeatureOut])
async def list_features(request: Request) -> list[McpFeatureOut]:
    """The features that declare tools, with the number of tools per level."""
    return table_of_features(_registry(request))


@router.get("/actions", response_model=list[McpActionOut])
async def list_actions(request: Request) -> list[McpActionOut]:
    """The table of exposed tools and their level."""
    return table_of_actions(_registry(request))


@router.post("/tokens", response_model=McpTokenCreated, status_code=201)
async def create_token(
    body: McpTokenCreateIn,
    request: Request,
    response: Response,
    current: InterfaceUserDep,
    db: Db,
) -> McpTokenCreated:
    """Creates a token; its value is returned only here, once."""
    service = TokenService(db, current.id, _known_features(request))
    token, plain = await service.create(body.label, body.features, body.mode, body.expires_in_days)
    response.headers["Cache-Control"] = "no-store"
    return McpTokenCreated(**token.model_dump(), token=plain)


@router.get("/tokens", response_model=list[McpTokenOut])
async def list_tokens(current: InterfaceUserDep, db: Db) -> list[McpTokenOut]:
    """My tokens (without their value), revoked ones included."""
    return await TokenService(db, current.id).mine()


@router.delete("/tokens/{token_id}", status_code=204, response_class=Response)
async def revoke_token(token_id: Id, current: InterfaceUserDep, db: Db) -> Response:
    """Revokes a token: it stops working immediately."""
    await TokenService(db, current.id).revoke(token_id)
    return Response(status_code=204)


@router.get("/confirmations", response_model=list[McpConfirmationOut])
async def list_confirmations(
    request: Request, current: InterfaceUserDep
) -> list[McpConfirmationOut]:
    """The "To confirm" requests, most recent first."""
    return await _confirmations(request, current.id).list()


@router.post("/confirmations/{confirmation_id}/confirm", response_model=McpConfirmationOut)
async def confirm(
    confirmation_id: Id, request: Request, current: InterfaceUserDep
) -> McpConfirmationOut:
    """Executes the request, once only; expired, refused or already handled: 409."""
    service = _confirmations(request, current.id)
    summary = await service.get(confirmation_id)
    result = await service.confirm(confirmation_id)
    if summary.action == "account_delete_data":
        return summary.model_copy(
            update={
                "status": "failed" if result.is_error else "confirmed",
                "decided_at": datetime.now(UTC),
            }
        )
    return await service.get(confirmation_id)


@router.post("/confirmations/{confirmation_id}/refuse", response_model=McpConfirmationOut)
async def refuse(
    confirmation_id: Id, request: Request, current: InterfaceUserDep
) -> McpConfirmationOut:
    """Refuses the request: it will never run."""
    return await _confirmations(request, current.id).refuse(confirmation_id)


@router.get("/calls", response_model=list[McpCallOut])
async def list_calls(current: InterfaceUserDep, db: Db, limit: Limit = 50) -> list[McpCallOut]:
    """The MCP call log (tool, level, code, duration), never their content."""
    return await CallsService(db, current.id).recent(limit)


@router.get("/changes", response_model=list[McpChangeOut])
async def list_changes(
    request: Request, current: InterfaceUserDep, limit: Limit = 50
) -> list[McpChangeOut]:
    """The changes made by Claude (level 2), undoable one call at a time."""
    return await ChangesService(request.app.state.session_factory, current.id).recent(limit)


@router.post("/changes/{call_id}/undo", response_model=McpUndoOut)
async def undo_changes(call_id: Id, request: Request, current: InterfaceUserDep) -> McpUndoOut:
    """Puts a call's rows back in their previous state, if none has changed since (409
    otherwise). A restored or removed memory is re-indexed afterwards, outside the call."""
    undone = await ChangesService(request.app.state.session_factory, current.id).undo(call_id)
    for sid in undone.cancelled_sessions:
        await request.app.state.runtime.runner.settle_cancelled(current.id, sid)
    schedule_indexing(request.app.state.memory, current.id)
    return McpUndoOut(call_id=undone.call_id, undone=undone.undone)
