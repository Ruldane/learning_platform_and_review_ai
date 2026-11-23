"""API de gestion de l'accès MCP (phase 10, P1, P15 à P19) : interrupteur général, tables des
features et des outils, jetons, demandes « À confirmer », journal des appels, changements et
annulation. Posée par 10.P (surface et schémas définitifs) ; 10.B1 a rempli l'interrupteur, les
jetons et le journal, 10.B2 les tables d'outils, les demandes « À confirmer » et les changements.
Ces routes sont **de l'interface** : la feature `mcp` n'est jamais exposée au MCP (niveau 4), un
jeton MCP n'ouvre jamais `/api/v1` (refusé ici en 403) et `get_interface_user` refuse même un appel
porté par une identité MCP."""

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
    """Les features qui déclarent des outils (`None` tant qu'aucune n'en déclare)."""
    gate = getattr(request.app.state, "mcp_gate", None)
    return gate.known_features if gate is not None else None


@router.get("/settings", response_model=McpSettingsOut)
async def get_settings(current: InterfaceUserDep, db: Db) -> McpSettingsOut:
    """L'interrupteur général du MCP (coupé par défaut)."""
    return await PrefsService(db, current.id).get()


@router.put("/settings", response_model=McpSettingsOut)
async def put_settings(body: McpSettingsIn, current: InterfaceUserDep, db: Db) -> McpSettingsOut:
    """Allume ou coupe tout l'accès MCP d'un geste."""
    return await PrefsService(db, current.id).set_enabled(body.enabled)


def _registry(request: Request) -> Registry:
    registry: Registry = request.app.state.mcp_registry
    return registry


def _confirmations(request: Request, user_id: str) -> ConfirmationService:
    """Le service des demandes de ce compte, avec l'envoyeur qui rejoue une demande confirmée."""
    service: ConfirmationService = request.app.state.mcp_confirmations(user_id)
    return service


@router.get("/features", response_model=list[McpFeatureOut])
async def list_features(request: Request) -> list[McpFeatureOut]:
    """Les features qui déclarent des outils, avec le nombre d'outils par niveau."""
    return table_of_features(_registry(request))


@router.get("/actions", response_model=list[McpActionOut])
async def list_actions(request: Request) -> list[McpActionOut]:
    """La table des outils exposés et de leur niveau."""
    return table_of_actions(_registry(request))


@router.post("/tokens", response_model=McpTokenCreated, status_code=201)
async def create_token(
    body: McpTokenCreateIn,
    request: Request,
    response: Response,
    current: InterfaceUserDep,
    db: Db,
) -> McpTokenCreated:
    """Crée un jeton ; sa valeur n'est rendue qu'ici, une seule fois."""
    service = TokenService(db, current.id, _known_features(request))
    token, plain = await service.create(body.label, body.features, body.mode, body.expires_in_days)
    response.headers["Cache-Control"] = "no-store"
    return McpTokenCreated(**token.model_dump(), token=plain)


@router.get("/tokens", response_model=list[McpTokenOut])
async def list_tokens(current: InterfaceUserDep, db: Db) -> list[McpTokenOut]:
    """Mes jetons (sans leur valeur), révoqués compris."""
    return await TokenService(db, current.id).mine()


@router.delete("/tokens/{token_id}", status_code=204, response_class=Response)
async def revoke_token(token_id: Id, current: InterfaceUserDep, db: Db) -> Response:
    """Révoque un jeton : il cesse de fonctionner aussitôt."""
    await TokenService(db, current.id).revoke(token_id)
    return Response(status_code=204)


@router.get("/confirmations", response_model=list[McpConfirmationOut])
async def list_confirmations(
    request: Request, current: InterfaceUserDep
) -> list[McpConfirmationOut]:
    """Les demandes « À confirmer », les plus récentes d'abord."""
    return await _confirmations(request, current.id).list()


@router.post("/confirmations/{confirmation_id}/confirm", response_model=McpConfirmationOut)
async def confirm(
    confirmation_id: Id, request: Request, current: InterfaceUserDep
) -> McpConfirmationOut:
    """Exécute la demande, une seule fois ; expirée, refusée ou déjà traitée : 409."""
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
    """Refuse la demande : elle ne s'exécutera jamais."""
    return await _confirmations(request, current.id).refuse(confirmation_id)


@router.get("/calls", response_model=list[McpCallOut])
async def list_calls(current: InterfaceUserDep, db: Db, limit: Limit = 50) -> list[McpCallOut]:
    """Le journal des appels MCP (outil, niveau, code, durée), jamais leur contenu."""
    return await CallsService(db, current.id).recent(limit)


@router.get("/changes", response_model=list[McpChangeOut])
async def list_changes(
    request: Request, current: InterfaceUserDep, limit: Limit = 50
) -> list[McpChangeOut]:
    """Les changements faits par Claude (niveau 2), annulables un appel à la fois."""
    return await ChangesService(request.app.state.session_factory, current.id).recent(limit)


@router.post("/changes/{call_id}/undo", response_model=McpUndoOut)
async def undo_changes(call_id: Id, request: Request, current: InterfaceUserDep) -> McpUndoOut:
    """Remet les lignes d'un appel dans leur état d'avant, si aucune n'a changé depuis (409
    sinon). Une mémoire restaurée ou retirée se réindexe ensuite, hors de l'appel."""
    undone = await ChangesService(request.app.state.session_factory, current.id).undo(call_id)
    for sid in undone.cancelled_sessions:
        await request.app.state.runtime.runner.settle_cancelled(current.id, sid)
    schedule_indexing(request.app.state.memory, current.id)
    return McpUndoOut(call_id=undone.call_id, undone=undone.undone)
