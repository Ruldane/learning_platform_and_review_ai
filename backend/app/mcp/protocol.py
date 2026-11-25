"""MCP server JSON-RPC 2.0 (phase 10, P10), written by hand: "Streamable HTTP" transport, stateless
(no session, `Mcp-Session-Id` never issued). Methods: `initialize`, `ping`, `tools/list`,
`tools/call`, `server/discover`; any notification (message without `id`) is accepted without a
reply and **never executed**, including a `tools/call` without `id`.

The engine knows neither the features nor the agents: it consumes a tool registry and a sender
(`ToolRegistry`, `Dispatcher`, provided by the composition). Authorization refusals (feature out
of scope, read-only token, limit reached) come out as `AppError` (403, 429), rendered in HTTP by
the entry point; a protocol error is a readable JSON-RPC error; a tool error is an `isError`
result that Claude can read."""

import json
import logging
from typing import Any

from app.core.caller import McpIdentity
from app.core.errors import AppError
from app.mcp.envelope import envelope
from app.mcp.instructions import INSTRUCTIONS
from app.mcp.tools import Dispatcher, ToolRegistry, ToolResult, ToolSpec

logger = logging.getLogger(__name__)

# Transport versions served with the `initialize` handshake (most recent first).
# Revision 2026-07-28 (stateless, no `initialize`) is not announced: a client that requests
# it gets 400 `-32022` with this list and falls back to one of them (fallback provided by the
# specification).
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
MAX_DEPTH = 24  # nesting of a message: beyond that, refused before any processing
MAX_RESULT_CHARS = 200_000
_ECHO_MAX = 60


class RpcError(Exception):
    """JSON-RPC error to return as is to the caller."""

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
    """Nesting deeper than `MAX_DEPTH` levels (iterative walk: no recursion)."""
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


def _tools_list(identity: McpIdentity, tools: ToolRegistry) -> dict[str, Any]:
    listed = [tool for tool in tools.list_for(identity) if tool.available_to(identity)]
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
    if not tool.in_scope(identity):
        raise AppError(
            "feature_not_allowed",
            f"This token does not open the feature '{tool.feature}'.",
            403,
            {"tool": tool.name, "level": tool.level},
        )
    if tool.level > 1 and identity.mode != "write":
        raise AppError(
            "write_not_allowed",
            "This token is read-only: it cannot call a tool that writes.",
            403,
            {"tool": tool.name, "level": tool.level},
        )


def _brief_content(data: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Images go into the MCP blocks, in place of base64 in the text."""
    images: list[dict[str, str]] = []
    messages = []
    for message in data["messages"]:
        blocks = message["content"]
        if isinstance(blocks, list):
            clean = []
            for block in blocks:
                if isinstance(block, dict) and block.get("type") == "image":
                    images.append(
                        {"type": "image", "data": block["base64"], "mimeType": block["mime_type"]}
                    )
                    clean.append({"type": "image", "index": len(images)})
                else:
                    clean.append(block)
            blocks = clean
        messages.append({**message, "content": blocks})
    return {**data, "messages": messages}, images


def _tool_result(tool: ToolSpec, outcome: ToolResult) -> dict[str, Any]:
    data = outcome.data
    images: list[dict[str, str]] = []
    if tool.name == "agents_play_brief" and not outcome.is_error:
        data, images = _brief_content(data)
    body = envelope(data, tool.untrusted, ok=not outcome.is_error)
    if outcome.notice:
        body["notice"] = f"{body['notice']} {outcome.notice}"
    text = json.dumps(body, ensure_ascii=False, default=str)
    if len(text) > MAX_RESULT_CHARS or sum(len(image["data"]) for image in images) > 8_000_000:
        too_big = {
            "error": {
                "code": "result_too_large",
                "message": "Result too large: ask for fewer items at a time.",
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
        "content": [{"type": "text", "text": text}, *images],
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
        raise RpcError(INVALID_PARAMS, "Tool name missing or invalid.")
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict):
        raise RpcError(INVALID_PARAMS, "A tool's arguments must be an object.")
    tool = tools.get(name)
    if tool is None:
        raise RpcError(
            INVALID_PARAMS,
            f"Unknown tool '{_clip(name)}'. List the available tools with tools/list.",
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
    raise RpcError(METHOD_NOT_FOUND, f"Unknown method '{_clip(method)}'.")


def _valid_id(rpc_id: Any) -> bool:
    return isinstance(rpc_id, str) or (isinstance(rpc_id, int) and not isinstance(rpc_id, bool))


async def handle_rpc(
    payload: dict[str, Any],
    identity: McpIdentity,
    tools: ToolRegistry,
    dispatcher: Dispatcher,
) -> dict[str, Any] | None:
    """Processes a JSON-RPC message. `None`: nothing to reply (notification, or the client's reply);
    the entry point then returns 202. Raises `AppError` 403 (scope, read-only) or 429."""
    if not isinstance(payload, dict) or _too_deep(payload):
        return rpc_error(None, INVALID_REQUEST, "Invalid or too deeply nested JSON-RPC message.")
    if "method" not in payload:
        if "result" in payload or "error" in payload:
            return None  # a client's reply to a request: accepted, no follow-up
        return rpc_error(None, INVALID_REQUEST, "JSON-RPC message without a method.")
    if "id" not in payload:
        return None  # notification: accepted, never executed
    rpc_id = payload["id"]
    method, params = payload["method"], payload.get("params")
    if not _valid_id(rpc_id) or payload.get("jsonrpc") != "2.0" or not isinstance(method, str):
        return rpc_error(None, INVALID_REQUEST, "Invalid JSON-RPC 2.0 request.")
    if params is None:
        params = {}
    if not isinstance(params, dict):
        return rpc_error(rpc_id, INVALID_PARAMS, "The params must be an object.")
    try:
        return _result(rpc_id, await _dispatch(method, params, identity, tools, dispatcher))
    except RpcError as exc:
        return rpc_error(rpc_id, exc.code, exc.message, exc.data)
    except AppError:
        raise
    except Exception as exc:  # never a 500: only the type is logged, never the content
        logger.error("MCP: internal error in '%s' (%s)", _clip(method), type(exc).__name__)
        return rpc_error(rpc_id, INTERNAL_ERROR, "MCP server internal error.")
