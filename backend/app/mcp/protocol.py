"""JSON-RPC 2.0 du serveur MCP (phase 10, P10), écrit à la main : transport « Streamable HTTP »,
sans état (aucune session, `Mcp-Session-Id` jamais émis). Méthodes : `initialize`, `ping`,
`tools/list`, `tools/call`, `server/discover` ; toute notification (message sans `id`) est acceptée
sans réponse et **jamais exécutée**, y compris un `tools/call` sans `id`.

Le moteur ne connaît ni les features ni les agents : il consomme un registre d'outils et un envoyeur
(`ToolRegistry`, `Dispatcher`, fournis par la composition). Les refus d'autorisation (feature hors
périmètre, jeton en lecture seule, limite atteinte) sortent en `AppError` (403, 429), rendus en HTTP
par le point d'entrée ; une erreur de protocole est une erreur JSON-RPC lisible ; une erreur de
l'outil est un résultat `isError` que Claude peut lire."""

import json
import logging
from typing import Any

from app.core.caller import McpIdentity
from app.core.errors import AppError
from app.mcp.envelope import envelope
from app.mcp.instructions import INSTRUCTIONS
from app.mcp.tools import Dispatcher, ToolRegistry, ToolResult, ToolSpec

logger = logging.getLogger(__name__)

# Versions du transport servies avec la poignée de main `initialize` (la plus récente d'abord).
# La révision 2026-07-28 (sans état, sans `initialize`) n'est pas annoncée : un client qui la
# demande reçoit 400 `-32022` avec cette liste et retombe sur l'une d'elles (repli prévu par la
# spécification).
SUPPORTED_VERSIONS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
SERVER_NAME = "tremplin"
SERVER_VERSION = "1.0.0"

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
HEADER_MISMATCH = -32020
UNSUPPORTED_VERSION = -32022

MAX_NAME_LENGTH = 80
MAX_DEPTH = 24  # imbrication d'un message : au-delà, refusé avant tout traitement
MAX_RESULT_CHARS = 200_000
_ECHO_MAX = 60


class RpcError(Exception):
    """Erreur JSON-RPC à rendre telle quelle à l'appelant."""

    def __init__(self, code: int, message: str, data: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


def rpc_error(rpc_id: Any, code: int, message: str, data: Any = None) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": rpc_id, "error": error}


def _result(rpc_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": rpc_id, "result": result}


def _too_deep(payload: Any) -> bool:
    """Imbrication de plus de `MAX_DEPTH` niveaux (parcours itératif : pas de récursion)."""
    stack: list[tuple[Any, int]] = [(payload, 1)]
    while stack:
        node, depth = stack.pop()
        if isinstance(node, dict | list):
            if depth > MAX_DEPTH:
                return True
            children = node.values() if isinstance(node, dict) else node
            stack.extend((child, depth + 1) for child in children)
    return False


def _clip(text: str) -> str:
    cleaned = "".join(ch if ch.isprintable() else " " for ch in text)
    return cleaned if len(cleaned) <= _ECHO_MAX else cleaned[:_ECHO_MAX] + "…"


def _initialize(params: dict[str, Any]) -> dict[str, Any]:
    asked = params.get("protocolVersion")
    version = asked if isinstance(asked, str) and asked in SUPPORTED_VERSIONS else None
    return {
        "protocolVersion": version or SUPPORTED_VERSIONS[0],
        "capabilities": {"tools": {"listChanged": False}},
        "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        "instructions": INSTRUCTIONS,
    }


def _discover() -> dict[str, Any]:
    return {
        "resultType": "complete",
        "supportedVersions": list(SUPPORTED_VERSIONS),
        "capabilities": {"tools": {"listChanged": False}},
        "_meta": {
            "io.modelcontextprotocol/serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION}
        },
        "instructions": INSTRUCTIONS,
        "ttlMs": 0,
        "cacheScope": "private",
    }


def _allowed_by_scope(tool: ToolSpec, identity: McpIdentity) -> bool:
    """Feature dans le périmètre du jeton ; mode `write` pour tout sauf une lecture."""
    return tool.feature in identity.features and (tool.level == 1 or identity.mode == "write")


def _tools_list(identity: McpIdentity, tools: ToolRegistry) -> dict[str, Any]:
    listed = [tool for tool in tools.list_for(identity) if _allowed_by_scope(tool, identity)]
    return {
        "resultType": "complete",
        "tools": [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": dict(tool.input_schema),
                "annotations": {
                    "readOnlyHint": tool.level == 1,
                    "destructiveHint": tool.level == 3,
                },
            }
            for tool in listed
        ],
        "ttlMs": 0,
        "cacheScope": "private",
    }


def _authorize(tool: ToolSpec, identity: McpIdentity) -> None:
    if tool.feature not in identity.features:
        raise AppError(
            "feature_not_allowed",
            f"Ce jeton n'ouvre pas la feature « {tool.feature} ».",
            403,
            {"tool": tool.name, "level": tool.level},
        )
    if tool.level > 1 and identity.mode != "write":
        raise AppError(
            "write_not_allowed",
            "Ce jeton est en lecture seule : il ne peut pas appeler un outil qui écrit.",
            403,
            {"tool": tool.name, "level": tool.level},
        )


def _tool_result(tool: ToolSpec, outcome: ToolResult) -> dict[str, Any]:
    body = envelope(outcome.data, tool.untrusted, ok=not outcome.is_error)
    if outcome.notice:
        body["notice"] = f"{body['notice']} {outcome.notice}"
    text = json.dumps(body, ensure_ascii=False, default=str)
    if len(text) > MAX_RESULT_CHARS:
        too_big = {
            "error": {
                "code": "result_too_large",
                "message": "Résultat trop volumineux : demande moins d'éléments à la fois.",
            }
        }
        text = json.dumps(envelope(too_big, (), ok=False), ensure_ascii=False)
        return {
            "resultType": "complete",
            "content": [{"type": "text", "text": text}],
            "isError": True,
        }
    return {
        "resultType": "complete",
        "content": [{"type": "text", "text": text}],
        "isError": outcome.is_error,
    }


def _error_outcome(exc: AppError) -> ToolResult:
    error = {"code": exc.code, "message": exc.message, "details": exc.details}
    return ToolResult(data={"error": error}, code=exc.status_code)


async def _tools_call(
    params: dict[str, Any], identity: McpIdentity, tools: ToolRegistry, dispatcher: Dispatcher
) -> dict[str, Any]:
    name = params.get("name")
    arguments = params.get("arguments")
    if not isinstance(name, str) or not name or len(name) > MAX_NAME_LENGTH:
        raise RpcError(INVALID_PARAMS, "Nom d'outil manquant ou invalide.")
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict):
        raise RpcError(INVALID_PARAMS, "Les arguments d'un outil forment un objet.")
    tool = tools.get(name)
    if tool is None:
        raise RpcError(
            INVALID_PARAMS,
            f"Outil inconnu : « {_clip(name)} ». Liste les outils disponibles avec tools/list.",
        )
    _authorize(tool, identity)
    try:
        outcome = await dispatcher.call(identity, tool, arguments)
    except AppError as exc:
        if exc.code == "rate_limited":
            raise
        outcome = _error_outcome(exc)
    return _tool_result(tool, outcome)


async def _dispatch(
    method: str,
    params: dict[str, Any],
    identity: McpIdentity,
    tools: ToolRegistry,
    dispatcher: Dispatcher,
) -> dict[str, Any]:
    if method == "initialize":
        return _initialize(params)
    if method == "ping":
        return {}
    if method == "server/discover":
        return _discover()
    if method == "tools/list":
        return _tools_list(identity, tools)
    if method == "tools/call":
        return await _tools_call(params, identity, tools, dispatcher)
    raise RpcError(METHOD_NOT_FOUND, f"Méthode inconnue : « {_clip(method)} ».")


def _valid_id(rpc_id: Any) -> bool:
    return isinstance(rpc_id, str) or (isinstance(rpc_id, int) and not isinstance(rpc_id, bool))


async def handle_rpc(
    payload: dict[str, Any],
    identity: McpIdentity,
    tools: ToolRegistry,
    dispatcher: Dispatcher,
) -> dict[str, Any] | None:
    """Traite un message JSON-RPC. `None` : rien à répondre (notification, ou réponse du client) ;
    le point d'entrée rend alors 202. Lève `AppError` 403 (périmètre, lecture seule) ou 429."""
    if not isinstance(payload, dict) or _too_deep(payload):
        return rpc_error(None, INVALID_REQUEST, "Message JSON-RPC invalide ou trop imbriqué.")
    if "method" not in payload:
        if "result" in payload or "error" in payload:
            return None  # la réponse d'un client à une requête : acceptée, sans suite
        return rpc_error(None, INVALID_REQUEST, "Message JSON-RPC sans méthode.")
    if "id" not in payload:
        return None  # notification : acceptée, jamais exécutée
    rpc_id = payload["id"]
    method, params = payload["method"], payload.get("params")
    if not _valid_id(rpc_id) or payload.get("jsonrpc") != "2.0" or not isinstance(method, str):
        return rpc_error(None, INVALID_REQUEST, "Requête JSON-RPC 2.0 invalide.")
    if params is None:
        params = {}
    if not isinstance(params, dict):
        return rpc_error(rpc_id, INVALID_PARAMS, "Les paramètres forment un objet.")
    try:
        return _result(rpc_id, await _dispatch(method, params, identity, tools, dispatcher))
    except RpcError as exc:
        return rpc_error(rpc_id, exc.code, exc.message, exc.data)
    except AppError:
        raise
    except Exception as exc:  # jamais une 500 : le type seul est journalisé, jamais le contenu
        logger.error("MCP : erreur interne dans « %s » (%s)", _clip(method), type(exc).__name__)
        return rpc_error(rpc_id, INTERNAL_ERROR, "Erreur interne du serveur MCP.")
