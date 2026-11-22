"""Échange local d'un code à usage unique et état réservé à l'interface."""

from fastapi import APIRouter, Depends, Request, Response

from app.core.caller import MCP_IDENTITY
from app.core.deps import Db, InterfaceUserDep
from app.core.errors import AppError
from app.features.mcp.relay_schemas import RelayCode, RelayStatus, RelayToken
from app.features.mcp.service.relay_pairing import RelayPairingService
from app.mcp.auth import check_local_origin, guard_interface_request

router = APIRouter(prefix="/mcp/relay", tags=["mcp"])
interface = APIRouter(dependencies=[Depends(guard_interface_request)])


def _service(request: Request, db: Db) -> RelayPairingService:
    return RelayPairingService(db, request.app.state.mcp_registry)


@interface.post("/pairing", status_code=201)
async def start_pairing(
    request: Request, response: Response, db: Db, current: InterfaceUserDep
) -> RelayCode:
    """Démarre l'appairage du relais du compte connecté."""
    code = await _service(request, db).start(current.id)
    response.headers["Cache-Control"] = "no-store"
    return RelayCode(code=code)


@interface.delete("/pairing", status_code=204, response_class=Response)
async def revoke_pairing(request: Request, db: Db, current: InterfaceUserDep) -> Response:
    """Annule un code en attente et révoque le jeton dédié du relais."""
    await _service(request, db).revoke(current.id)
    return Response(status_code=204)


@interface.get("/status")
async def pairing_status(request: Request, db: Db, current: InterfaceUserDep) -> RelayStatus:
    """État de l'appairage et portées manquantes du compte connecté."""
    return await _service(request, db).status(current.id)


@router.post("/exchange", status_code=201)
async def exchange_pairing(
    code: RelayCode, request: Request, response: Response, db: Db
) -> RelayToken:
    """Échange par le relais local. Le code désigne le compte, indépendamment des cookies."""
    check_local_origin(request)
    if "origin" in request.headers or MCP_IDENTITY.get() is not None:
        raise AppError("relay_only", "Échange réservé au relais local de Tremplin.", 403)
    allowed = request.app.state.mcp_gate.user_allowed
    token = await _service(request, db).exchange(code.code, allowed)
    response.headers["Cache-Control"] = "no-store"
    return RelayToken(token=token)


router.include_router(interface)
