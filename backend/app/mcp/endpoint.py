"""Le point d'entrée HTTP du MCP : `POST /mcp` (hors `/api/v1`, hors contrat), transport
« Streamable HTTP » sans état. `GET` et `DELETE` : 405 (pas de flux serveur ni de session) ; tout
refus (origine, jeton, interrupteur, taille, limite) est une réponse `{error: {code, message,
details}}` lisible, avec le bon code HTTP ; rien n'est exécuté avant que la porte ait ouvert.

Ordre : origine et hôte, jeton (courte session, validée avant tout travail : un appel long ne tient
jamais de transaction ouverte), corps (1 Mo au plus), JSON, en-têtes du transport, puis le
JSON-RPC. Une 500 n'est possible que par une panne de l'infrastructure, jamais par un message."""

import json
import logging
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse, Response

from app.core.errors import AppError
from app.mcp.auth import McpRefusal, authenticate
from app.mcp.protocol import (
    HEADER_MISMATCH,
    INVALID_REQUEST,
    PARSE_ERROR,
    SUPPORTED_VERSIONS,
    UNSUPPORTED_VERSION,
    handle_rpc,
    rpc_error,
)
from app.mcp.tools import McpGate

logger = logging.getLogger(__name__)

_NO_STORE = {"Cache-Control": "no-store"}
_RPC_HTTP_400 = frozenset({PARSE_ERROR, INVALID_REQUEST})


def refusal(exc: AppError) -> JSONResponse:
    """Le refus au format d'erreur de l'application, avec les en-têtes que le client attend."""
    headers = dict(_NO_STORE)
    if exc.status_code == 401:
        headers["WWW-Authenticate"] = 'Bearer realm="tremplin-mcp"'
    if exc.status_code == 429 and exc.details and "retry_after" in exc.details:
        headers["Retry-After"] = str(exc.details["retry_after"])
    body = {"error": {"code": exc.code, "message": exc.message, "details": exc.details}}
    return JSONResponse(body, status_code=exc.status_code, headers=headers)


def _rpc_response(message: dict[str, Any], status: int = 200) -> JSONResponse:
    return JSONResponse(message, status_code=status, headers=_NO_STORE)


def _as_int(text: str) -> int:
    """Un entier lu d'un en-tête, ou 0 s'il est hors limites de Python (jamais une erreur)."""
    try:
        return int(text)
    except ValueError:
        return 0


async def _read_body(request: Request, limit: int) -> bytes:
    """Le corps, lu par morceaux et abandonné au dépassement de `limit` octets (413)."""
    too_large = AppError("body_too_large", "Corps trop volumineux : 1 Mo au maximum.", 413)
    declared = request.headers.get("content-length", "")
    if declared.isascii() and declared.isdecimal() and _as_int(declared) > limit:
        raise too_large
    chunks: list[bytes] = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > limit:
            raise too_large
        chunks.append(chunk)
    return b"".join(chunks)


def _reject_constant(name: str) -> Any:
    raise ValueError(f"constante JSON refusée : {name}")


def _parse(body: bytes) -> Any:
    """Le JSON du corps, ou `None` (illisible, `NaN`, trop imbriqué pour Python)."""
    try:
        return json.loads(body, parse_constant=_reject_constant)
    except (ValueError, RecursionError):
        return None


def _check_headers(request: Request, payload: dict[str, Any]) -> JSONResponse | None:
    """`MCP-Protocol-Version` connue, `Mcp-Method` égal à la méthode du corps ; sinon 400."""
    method = payload.get("method")
    version = request.headers.get("mcp-protocol-version")
    if version is not None and method != "initialize" and version not in SUPPORTED_VERSIONS:
        data = {"supported": list(SUPPORTED_VERSIONS), "requested": version[:40]}
        message = rpc_error(
            None, UNSUPPORTED_VERSION, "Version du protocole non prise en charge.", data
        )
        return _rpc_response(message, 400)
    declared = request.headers.get("mcp-method")
    if declared is not None and declared != method:
        message = rpc_error(
            None, HEADER_MISMATCH, "L'en-tête Mcp-Method ne correspond pas au corps."
        )
        return _rpc_response(message, 400)
    return None


async def _serve_post(request: Request) -> Response:
    gate: McpGate | None = getattr(request.app.state, "mcp_gate", None)
    if gate is None:
        raise AppError("mcp_unavailable", "Le serveur MCP n'est pas prêt.", 503)
    try:
        async with request.app.state.session_factory() as db:
            identity = await authenticate(request, db)
            await db.commit()  # `last_used_at` ; la session est fermée avant tout travail long
    except McpRefusal as exc:
        await gate.refusals(exc.user_id, exc.token_id, f"refused:{exc.code}", 0, exc.status_code)
        raise
    body = await _read_body(request, request.app.state.settings.mcp_body_limit)
    payload = _parse(body)
    if not isinstance(payload, dict):
        message = rpc_error(None, PARSE_ERROR, "JSON illisible, ou message qui n'est pas un objet.")
        return _rpc_response(message, 400)
    if (refused := _check_headers(request, payload)) is not None:
        return refused
    try:
        answer = await handle_rpc(payload, identity, gate.tools, gate.dispatcher)
    except AppError as exc:
        details = exc.details or {}
        if exc.status_code == 403 and "tool" in details:  # périmètre ou lecture seule
            args = (identity.user_id, identity.token_id, details["tool"], details["level"])
            await gate.refusals(*args, 403)
        raise
    if answer is None:
        return Response(status_code=202, headers=_NO_STORE)
    code = answer.get("error", {}).get("code")
    return _rpc_response(answer, 400 if code in _RPC_HTTP_400 else 200)


async def mcp_endpoint(request: Request) -> Response:
    """`POST /mcp`. Toute autre méthode : 405."""
    if request.method != "POST":
        return JSONResponse(
            {"error": {"code": "http_error", "message": "Méthode non autorisée.", "details": None}},
            status_code=405,
            headers={"Allow": "POST", **_NO_STORE},
        )
    try:
        return await _serve_post(request)
    except AppError as exc:
        return refusal(exc)
    except Exception as exc:  # panne d'infrastructure : le type seul est journalisé
        logger.error("MCP : erreur interne (%s)", type(exc).__name__)
        body = {"error": {"code": "internal_error", "message": "Erreur interne.", "details": None}}
        return JSONResponse(body, status_code=500, headers=_NO_STORE)
