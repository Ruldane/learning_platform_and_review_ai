"""L'envoyeur du MCP (phase 10, P12, P14, P15) : un appel d'outil devient **la vraie requête** de la
route, envoyée en interne à l'application (`httpx.ASGITransport`), sous l'identité du jeton. Mêmes
validations, même isolation par compte, mêmes contrôles que l'interface.

`MCP_IDENTITY` n'est écrite qu'ici (`internal_request`) : posée avant la requête, remise dans un
`finally`. Elle ne vient jamais d'un en-tête ni d'un cookie, et la requête interne n'en porte aucun.

Par niveau : 1 envoi simple ; 2 envoi sous un `ChangeRecorder` (historique et annulation) ; 3
contrôle préalable éventuel puis demande « À confirmer », rien n'est envoyé avant le clic ; un
graphe est un `POST /sessions` dont l'`input` est validé par le `input_model` (la route)."""

import asyncio
import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.caller import MCP_IDENTITY, McpIdentity
from app.db.base import new_id
from app.mcp.arguments import ArgumentError, ToolRequest, build_request, check_arguments
from app.mcp.base import PrecheckInput, Verdict
from app.mcp.confirm import ConfirmationPort, StoredRequest, summarize
from app.mcp.envelope import fence
from app.mcp.recorder import ChangeRecorder, install_recorder_events
from app.mcp.registry import Registry
from app.mcp.results import (
    filter_fields,
    form_fields,
    read_response,
    result_ids,
    translate_validation,
)
from app.mcp.schema import API_PREFIX, never_reachable
from app.mcp.tools import ToolResult, ToolSpec

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_S = 90.0
PRECHECK_TIMEOUT_S = 60.0
_BAD_PATH_CHARS = ("..", "?", "#", "%", "\\", "\x00")


@dataclass(frozen=True)
class InternalResponse:
    """La réponse de la route : code HTTP et corps (JSON lu, `None` si vide)."""

    status: int
    data: Any


def _error(status: int, code: str, message: str, details: Any = None) -> InternalResponse:
    return InternalResponse(
        status, {"error": {"code": code, "message": message, "details": details}}
    )


async def internal_request(
    app: FastAPI,
    identity: McpIdentity,
    method: str,
    path: str,
    params: Mapping[str, Any],
    body: Any,
    *,
    form: bool = False,
) -> InternalResponse:
    """Envoie la requête à l'application, sous `identity` (le propriétaire du jeton, jamais un
    autre), sans cookie ni en-tête d'authentification. `path` : sans `/api/v1`. Les routes de
    niveau 4 (connexion, compte, MCP, clés, modèles) ne sont jamais atteintes, quelle que soit la
    demande."""
    if not path.startswith("/") or never_reachable(path) or any(c in path for c in _BAD_PATH_CHARS):
        return _error(403, "route_not_reachable", "Cette route n'est pas ouverte au MCP.")
    options: dict[str, Any] = {"params": dict(params) or None}
    if form:
        options["files"] = form_fields(body)
    elif body is not None:
        options["json"] = body
    token = MCP_IDENTITY.set(identity)
    try:
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as http:
            call = http.request(method, API_PREFIX + path, **options)
            response = await asyncio.wait_for(call, REQUEST_TIMEOUT_S)
    except TimeoutError:
        return _error(504, "tool_timeout", "La route a mis trop de temps à répondre.")
    finally:
        MCP_IDENTITY.reset(token)
    return InternalResponse(response.status_code, read_response(response))


class McpDispatcher:
    """L'envoyeur réel (la porte l'enveloppe des limites et du journal, `GuardedDispatcher`)."""

    def __init__(
        self,
        app: FastAPI,
        session_factory: async_sessionmaker[AsyncSession],
        registry: Registry,
        confirmations: Callable[[str], ConfirmationPort],
    ) -> None:
        self._app = app
        self._factory = session_factory
        self._registry = registry
        self._confirmations = confirmations
        install_recorder_events()

    async def call(
        self, identity: McpIdentity, tool: ToolSpec, arguments: dict[str, Any]
    ) -> ToolResult:
        try:
            check_arguments(tool.input_schema, arguments)
            request = self._request(tool, arguments)
        except ArgumentError as exc:
            data = {"error": {"code": "invalid_arguments", "message": exc.message}}
            return ToolResult(data=data, code=422, ids={})
        if tool.level == 3:
            return await self._pend(identity, tool, request)
        if tool.level == 2 and tool.graph is None:
            return await self._recorded(identity, tool, request, arguments)
        response = await self._send(identity, request)
        return self._result(tool, arguments, response)

    @staticmethod
    def _request(tool: ToolSpec, arguments: Mapping[str, Any]) -> ToolRequest:
        if tool.graph is not None:
            body = {"graph": tool.graph, "input": dict(arguments)}
            return ToolRequest("POST", "/sessions", {}, body)
        if tool.plan is None:
            raise ArgumentError("Outil sans route.")
        return build_request(tool.plan, arguments)

    async def _send(self, identity: McpIdentity, request: ToolRequest) -> InternalResponse:
        """La requête ; avec `merge_from`, le corps est la lecture actuelle dont seuls les champs
        listés changent (lue maintenant, jamais gardée)."""
        body = request.body
        if request.merge_path is not None:
            base = await internal_request(self._app, identity, "GET", request.merge_path, {}, None)
            if base.status >= 400:
                return base
            if not isinstance(base.data, dict):
                return _error(502, "merge_failed", "Lecture de base inattendue.")
            body = {**base.data, **(body or {})}
        return await internal_request(
            self._app, identity, request.method, request.path, request.params, body,
            form=request.form,
        )  # fmt: skip

    async def _recorded(
        self, identity: McpIdentity, tool: ToolSpec, request: ToolRequest, arguments: dict[str, Any]
    ) -> ToolResult:
        """Niveau 2 : la requête sous un `ChangeRecorder` ; l'historique n'est gardé que si elle a
        réussi, sous l'identifiant de l'appel (celui de la ligne du journal)."""
        call_id = new_id()
        recorder = ChangeRecorder(self._factory, call_id, identity.user_id)
        async with recorder:
            response = await self._send(identity, request)
        if response.status < 400:
            try:
                await recorder.persist()
            except Exception as exc:  # une panne d'historique ne défait pas l'appel déjà fait
                logger.error("MCP : historique de l'appel impossible (%s)", type(exc).__name__)
        return self._result(tool, arguments, response, call_id)

    def _result(
        self,
        tool: ToolSpec,
        arguments: Mapping[str, Any],
        response: InternalResponse,
        call_id: str | None = None,
    ) -> ToolResult:
        data = response.data
        if response.status == 422:
            data = translate_validation(data, tool)
        elif response.status < 400:
            data = self._fence_sessions(filter_fields(data, tool.response_fields))
        return ToolResult(
            data={} if data is None else data,
            code=response.status,
            ids=result_ids(arguments, data),
            call_id=call_id,
        )

    def _fence_sessions(self, data: Any) -> Any:
        """Le résultat d'une session d'un graphe qui lit le web est rendu comme donnée non fiable
        quand Claude suit la session (`McpGraph.untrusted`)."""
        paths = self._registry.graph_untrusted
        if isinstance(data, list):
            return [self._fence_sessions(item) for item in data]
        if isinstance(data, dict) and isinstance(data.get("graph"), str) and data["graph"] in paths:
            return fence(data, paths[data["graph"]])
        return data

    async def _pend(
        self, identity: McpIdentity, tool: ToolSpec, request: ToolRequest
    ) -> ToolResult:
        """Niveau 3 : rien n'est envoyé. Le contrôle préalable (s'il y en a un) et la requête sont
        rangés dans une demande « À confirmer »."""
        verdict = await self._precheck(identity, tool, request)
        stored = StoredRequest(
            tool.name, request, identity.label, tuple(sorted(identity.features)), identity.mode
        )
        pending = await self._confirmations(identity.user_id).create(
            identity, stored, summarize(tool, request), verdict
        )
        data = {
            "status": "pending_confirmation",
            "confirmation_id": pending.id,
            "expires_at": pending.expires_at.isoformat(),
        }
        return ToolResult(data=data, code=202, ids={"confirmation_id": pending.id})

    @staticmethod
    async def _precheck(
        identity: McpIdentity, tool: ToolSpec, request: ToolRequest
    ) -> dict[str, Any] | None:
        if tool.precheck is None:
            return None
        asked = PrecheckInput(
            user_id=identity.user_id,
            method=request.method,
            path=request.path,
            params=request.params,
            body=request.body,
        )
        try:
            verdict = await asyncio.wait_for(tool.precheck(asked), PRECHECK_TIMEOUT_S)
        except Exception as exc:  # jamais un blocage silencieux : la demande dit qu'il manque
            logger.error("MCP : contrôle préalable impossible (%s)", type(exc).__name__)
            verdict = Verdict(ok=False, reasons=("Le contrôle préalable n'a pas pu se faire.",))
        return {"ok": verdict.ok, "reasons": list(verdict.reasons), "summary": verdict.summary}

    async def run_stored(self, identity: McpIdentity, stored: StoredRequest) -> ToolResult:
        """Exécute une demande confirmée, sous l'identité enregistrée (jamais d'historique : une
        action de niveau 3 ne s'annule pas)."""
        tool = self._registry.get(stored.tool)
        if tool is None:
            data = {"error": {"code": "unknown_tool", "message": "Outil retiré depuis."}}
            return ToolResult(data=data, code=404)
        response = await self._send(identity, stored.request)
        return self._result(tool, {}, response)
