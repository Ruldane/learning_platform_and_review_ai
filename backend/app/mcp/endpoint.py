"""The MCP HTTP entry point: `POST /mcp` (outside `/api/v1`, outside the contract), a stateless
"Streamable HTTP" transport. `GET` and `DELETE`: 405 (no server stream or session); any refusal
(origin, token, switch, size, limit) is a readable `{error: {code, message, details}}` response,
with the right HTTP code; nothing runs before the gate has opened.

Order: origin and host, token (short session, validated before any work: a long call never holds
an open transaction), body (1 MB at most), JSON, transport headers, then the JSON-RPC. A 500 is
possible only through an infrastructure failure, never through a message."""

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
    """The refusal in the application's error format, with the headers the client expects."""
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
    """An integer read from a header, or 0 if it is out of Python's range (never an error)."""
    try:
        return int(text)
    except ValueError:
        return 0


async def _read_body(request: Request, limit: int) -> bytes:
    """The body, read in chunks and dropped when `limit` bytes are exceeded (413)."""
    too_large = AppError("body_too_large", "Body too large: 1 MB at most.", 413)
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
    raise ValueError(f"JSON constant refused: {name}")


def _parse(body: bytes) -> Any:
    """The body's JSON, or `None` (unreadable, `NaN`, too nested for Python)."""
    try:
        return json.loads(body, parse_constant=_reject_constant)
    except (ValueError, RecursionError):
        return None


def _check_headers(request: Request, payload: dict[str, Any]) -> JSONResponse | None:
    """Known `MCP-Protocol-Version`, and `Mcp-Method` equal to the body's method; otherwise 400."""
    method = payload.get("method")
    version = request.headers.get("mcp-protocol-version")
    if version is not None and method != "initialize" and version not in SUPPORTED_VERSIONS:
        data = {"supported": list(SUPPORTED_VERSIONS), "requested": version[:40]}
        message = rpc_error(None, UNSUPPORTED_VERSION, "Protocol version not supported.", data)
        return _rpc_response(message, 400)
    declared = request.headers.get("mcp-method")
    if declared is not None and declared != method:
        message = rpc_error(None, HEADER_MISMATCH, "The Mcp-Method header does not match the body.")
        return _rpc_response(message, 400)
    return None


async def _serve_post(request: Request) -> Response:
    gate: McpGate | None = getattr(request.app.state, "mcp_gate", None)
    if gate is None:
        raise AppError("mcp_unavailable", "The MCP server is not ready.", 503)
    try:
        async with request.app.state.session_factory() as db:
            identity = await authenticate(request, db)
            await db.commit()  # `last_used_at`; the session is closed before any long work
    except McpRefusal as exc:
        await gate.refusals(exc.user_id, exc.token_id, f"refused:{exc.code}", 0, exc.status_code)
        raise
    body = await _read_body(request, request.app.state.settings.mcp_body_limit)
    payload = _parse(body)
    if not isinstance(payload, dict):
        message = rpc_error(
            None, PARSE_ERROR, "Unreadable JSON, or a message that is not an object."
        )
        return _rpc_response(message, 400)
    if (refused := _check_headers(request, payload)) is not None:
        return refused
    try:
        answer = await handle_rpc(payload, identity, gate.tools, gate.dispatcher)
    except AppError as exc:
        details = exc.details or {}
        if exc.status_code == 403 and "tool" in details:  # scope or read-only
            args = (identity.user_id, identity.token_id, details["tool"], details["level"])
            await gate.refusals(*args, 403)
        raise
    if answer is None:
        return Response(status_code=202, headers=_NO_STORE)
    code = answer.get("error", {}).get("code")
    return _rpc_response(answer, 400 if code in _RPC_HTTP_400 else 200)


async def mcp_endpoint(request: Request) -> Response:
    """`POST /mcp`. Any other method: 405."""
    if request.method != "POST":
        return JSONResponse(
            {"error": {"code": "http_error", "message": "Method not allowed.", "details": None}},
            status_code=405,
            headers={"Allow": "POST", **_NO_STORE},
        )
    try:
        return await _serve_post(request)
    except AppError as exc:
        return refusal(exc)
    except Exception as exc:  # infrastructure failure: only the type is logged
        logger.error("MCP : erreur interne (%s)", type(exc).__name__)
        body = {"error": {"code": "internal_error", "message": "Erreur interne.", "details": None}}
        return JSONResponse(body, status_code=500, headers=_NO_STORE)
