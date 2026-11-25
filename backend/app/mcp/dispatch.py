"""The MCP sender (phase 10, P12, P14, P15): a tool call becomes **the real request** of the route,
sent internally to the application (`httpx.ASGITransport`), under the token's identity. Same
validations, same per-account isolation, same checks as the interface.

`MCP_IDENTITY` is written only here (`internal_request`): set before the request, restored in a
`finally`. It never comes from a header or a cookie, and the internal request carries none.

By level: 1 simple send; 2 send under a `ChangeRecorder` (history and undo); 3 optional precheck,
then a « À confirmer » request; nothing is sent before the click. A graph is a `POST /sessions`
whose `input` is validated by the `input_model` (the route)."""

import asyncio
import logging
from collections.abc import Callable, Mapping
from typing import Any

import httpx
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.caller import MCP_CONFIRMED, MCP_IDENTITY, McpIdentity
from app.db.base import new_id
from app.mcp.arguments import ArgumentError, ToolRequest, build_request, check_arguments
from app.mcp.confirm import ConfirmationPort, StoredRequest, check_before_confirmation, summarize
from app.mcp.played import PlayLauncher
from app.mcp.recorder import ChangeRecorder, install_recorder_events
from app.mcp.registry import Registry
from app.mcp.results import (
    InternalResponse,
    artifact_response,
    fence_sessions,
    filter_fields,
    form_fields,
    internal_error,
    read_response,
    result_ids,
    timed_out,
    translate_validation,
)
from app.mcp.routes import RouteIndex
from app.mcp.schema import API_PREFIX, never_reachable
from app.mcp.target import label_of, reader_of_target
from app.mcp.tools import ToolResult, ToolSpec

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_S = 90.0
_BAD_PATH_CHARS = ("..", "?", "#", "%", "\\", "\x00")
_NO_HISTORY = {
    "overflow": "Too many rows touched to keep the history",
    "failed": "The history of this call could not be written",
    "empty": "No database row was recorded for this call",
}


async def internal_request(
    app: FastAPI,
    identity: McpIdentity,
    method: str,
    path: str,
    params: Mapping[str, Any],
    body: Any,
    *,
    form: bool = False,
    confirmed: bool = False,
    artifact: bool = False,
) -> InternalResponse:
    """Sends the request to the application, under `identity` (the token's owner, never anyone
    else), with no cookie or authentication header. `path`: without `/api/v1`. Level 4 routes
    (sign-in, account, MCP, keys, models) are never reached, whatever the request."""
    if (
        not path.startswith("/")
        or never_reachable(path, method)
        or any(c in path for c in _BAD_PATH_CHARS)
    ):
        return internal_error(403, "route_not_reachable", "This route is not open to MCP.")
    options: dict[str, Any] = {"params": dict(params) or None}
    if form:
        options["files"] = form_fields(body)
    elif body is not None:
        options["json"] = body
    token = MCP_IDENTITY.set(identity)
    confirmation = MCP_CONFIRMED.set(confirmed)
    try:
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as http:
            call = http.request(method, API_PREFIX + path, **options)
            response = await asyncio.wait_for(call, REQUEST_TIMEOUT_S)
    except TimeoutError:
        return internal_error(504, "tool_timeout", "The route took too long to respond.")
    finally:
        MCP_CONFIRMED.reset(confirmation)
        MCP_IDENTITY.reset(token)
    if artifact and 200 <= response.status_code < 300:
        local_url = response.request.url.raw_path.decode() if method == "GET" else None
        return InternalResponse(response.status_code, artifact_response(response, local_url))
    return InternalResponse(response.status_code, read_response(response))


class McpDispatcher:
    """The real sender (the gate wraps it with the limits and the journal, `GuardedDispatcher`)."""

    def __init__(
        self,
        app: FastAPI,
        session_factory: async_sessionmaker[AsyncSession],
        registry: Registry,
        confirmations: Callable[[str], ConfirmationPort],
    ) -> None:
        self._app = app
        self._routes = RouteIndex(app.openapi())
        self._factory = session_factory
        self._registry = registry
        self._confirmations = confirmations
        self.play_launch = PlayLauncher(registry, self._routes, self._send)
        install_recorder_events()

    async def call(
        self, identity: McpIdentity, tool: ToolSpec, arguments: dict[str, Any]
    ) -> ToolResult:
        try:
            check_arguments(tool.input_schema, arguments)
            if tool.manual_url:
                return ToolResult(data={"local_url": tool.manual_url})
            request = self._request(tool, arguments)
            self._routes.ensure_declared(tool, request)
        except ArgumentError as exc:
            data = {"error": {"code": "invalid_arguments", "message": exc.message}}
            return ToolResult(data=data, code=422, ids={})
        if tool.level == 3:
            return await self._pend(identity, tool, request)
        if tool.level == 2 and tool.graph is None:
            return await self._recorded(identity, tool, request)
        response = await self._send(identity, request, artifact=tool.artifact)
        return self._result(tool, response)

    @staticmethod
    def _request(tool: ToolSpec, arguments: Mapping[str, Any]) -> ToolRequest:
        if tool.graph is not None:
            body = {"graph": tool.graph, "input": dict(arguments)}
            return ToolRequest("POST", "/sessions", {}, body)
        if tool.plan is None:
            raise ArgumentError("Tool without a route.")
        return build_request(tool.plan, arguments)

    async def _send(
        self,
        identity: McpIdentity,
        request: ToolRequest,
        *,
        confirmed: bool = False,
        artifact: bool = False,
    ) -> InternalResponse:
        """The request; with `merge_from`, the body is the current read, of which only the listed
        fields
        change (read now, never kept)."""
        body = request.body
        if request.merge_path is not None:
            base = await internal_request(self._app, identity, "GET", request.merge_path, {}, None)
            if base.status >= 400:
                return base
            if not isinstance(base.data, dict):
                return internal_error(502, "merge_failed", "Lecture de base inattendue.")
            body = {**base.data, **(body or {})}
        return await internal_request(
            self._app, identity, request.method, request.path, request.params, body,
            form=request.form, confirmed=confirmed, artifact=artifact,
        )  # fmt: skip

    async def _recorded(
        self, identity: McpIdentity, tool: ToolSpec, request: ToolRequest
    ) -> ToolResult:
        """Level 2: the request under a `ChangeRecorder`; the history is kept only if it succeeded,
        under
        the call's identifier (that of the journal row)."""
        call_id = new_id()
        recorder = ChangeRecorder(self._factory, call_id, identity.user_id)
        async with recorder:
            response = await self._send(identity, request)
        why: str | None = None
        if response.status < 400:
            try:
                kept = await recorder.persist()
                why = None if kept else ("overflow" if recorder.overflow else "empty")
            except Exception as exc:  # a history failure does not undo the call already made
                logger.error("MCP : historique de l'appel impossible (%s)", type(exc).__name__)
                why = "failed"
        return self._result(tool, response, call_id, why)

    def _result(
        self,
        tool: ToolSpec,
        response: InternalResponse,
        call_id: str | None = None,
        no_history: str | None = None,
    ) -> ToolResult:
        """`no_history`: a successful level 2 call without history says so (`notice`, journal)."""
        data = response.data
        if response.status == 504 and tool.level >= 2:  # the route may have written (M7)
            return timed_out(data, call_id)
        if response.status == 422:
            data = translate_validation(data, tool)
        elif response.status < 400:
            data = fence_sessions(
                filter_fields(data, tool.response_fields), self._registry.graph_untrusted
            )
        ids = result_ids(data) if 200 <= response.status < 300 else {}
        notice = None
        if no_history is not None:
            ids["history"] = "none"
            notice = f"{_NO_HISTORY[no_history]}: this call cannot be undone from the app."
        return ToolResult(
            data={} if data is None else data,
            code=response.status,
            ids=ids,
            call_id=call_id,
            notice=notice,
        )

    async def _pend(
        self, identity: McpIdentity, tool: ToolSpec, request: ToolRequest
    ) -> ToolResult:
        """Level 3: nothing is sent. The precheck (if any) and the request are filed in a « À
        confirmer »
        request."""
        port = self._confirmations(identity.user_id)
        await port.ensure_room(identity)  # the cap first: the check may cost a model call
        verdict = await check_before_confirmation(identity, tool, request)
        stored = StoredRequest(
            tool.name,
            request,
            identity.label,
            tuple(sorted(identity.features)),
            identity.mode,
            tool.route[1] if tool.route else None,
            await self._target_label(identity, tool, request),
        )
        pending = await port.create(identity, stored, summarize(tool, request), verdict)
        data = {
            "status": "pending_confirmation",
            "confirmation_id": pending.id,
            "expires_at": pending.expires_at.isoformat(),
        }
        return ToolResult(data=data, code=202, ids={"confirmation_id": pending.id})

    async def _target_label(
        self, identity: McpIdentity, tool: ToolSpec, request: ToolRequest
    ) -> str | None:
        """The readable label of the target (« Company — Title »), read by the GET route of the same
        resource when it is declared (see `app/mcp/target.py`); `None` otherwise. Read under the
        token's identity, shown to January only."""
        found = reader_of_target(self._registry, tool, request.path)
        if found is None:
            return None
        reader, path = found
        try:
            read = await internal_request(self._app, identity, "GET", path, {}, None)
        except Exception as exc:  # the label is only a convenience: never a block
            logger.error("MCP: target label failed (%s)", type(exc).__name__)
            return None
        return label_of(read.data, reader) if read.status == 200 else None

    async def recheck(self, identity: McpIdentity, stored: StoredRequest) -> dict[str, Any] | None:
        """Replays the precheck of a pending request (`None`: the tool no longer has one)."""
        tool = self._registry.get(stored.tool)
        if tool is None:
            return None
        return await check_before_confirmation(identity, tool, stored.request)

    async def run_stored(self, identity: McpIdentity, stored: StoredRequest) -> ToolResult:
        """Runs a confirmed request, under the recorded identity (never history: a level 3 action
        cannot
        be undone)."""
        tool = self._registry.get(stored.tool)
        if tool is None or tool.level != 3 or not tool.available_to(identity):
            data = {"error": {"code": "unknown_tool", "message": "Tool removed since."}}
            return ToolResult(data=data, code=404)
        try:
            if tool.route is None or stored.request.method != tool.route[0]:
                raise ArgumentError("This request no longer matches the tool.")
            self._routes.ensure_declared(tool, stored.request)
        except ArgumentError as exc:
            data = {"error": {"code": "invalid_arguments", "message": exc.message}}
            return ToolResult(data=data, code=422)
        response = await self._send(
            identity, stored.request, confirmed=True, artifact=tool.artifact
        )
        return self._result(tool, response)
