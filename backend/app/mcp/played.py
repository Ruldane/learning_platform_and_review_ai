"""Checks the launch tool and keeps the permissions of its route."""

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any

from app.core.caller import MCP_IDENTITY, McpIdentity
from app.core.errors import AppError
from app.core.played import PLAY_CONTEXT, PlayClient, PlayContext
from app.mcp.arguments import ArgumentError, ToolRequest, build_request, check_arguments
from app.mcp.registry import Registry
from app.mcp.results import InternalResponse
from app.mcp.routes import RouteIndex


def play_identity(user_id: str, *, write: bool = False) -> McpIdentity:
    identity = MCP_IDENTITY.get()
    if (
        not identity
        or identity.user_id != user_id
        or "sessions" not in identity.features
        or (write and identity.mode != "write")
    ):
        raise AppError("play_forbidden", "Insufficient MCP access for this session.", 403)
    return identity


def launch_request(
    registry: Registry,
    routes: RouteIndex,
    identity: McpIdentity,
    launch: str,
    arguments: Mapping[str, Any],
) -> tuple[ToolRequest, str]:
    tool = registry.play_tool(launch)
    if tool is None or tool.feature not in identity.features:
        raise AppError("play_forbidden", "Launch tool outside the token's scope.", 403)
    graph = tool.graph or tool.launches
    if not graph or tool.level != 2:
        raise AppError("not_a_launch", "This tool does not launch a playable workflow.", 422)
    if registry.graph_features.get(graph) not in identity.features:
        raise AppError("play_forbidden", "Workflow outside the token's scope.", 403)
    try:
        check_arguments(tool.input_schema, arguments)
        if tool.graph:
            return ToolRequest(
                "POST", "/sessions", {}, {"graph": tool.graph, "input": dict(arguments)}
            ), graph
        if tool.plan:
            request = build_request(tool.plan, arguments)
            routes.ensure_declared(tool, request)
            return request, graph
    except ArgumentError:
        raise AppError("invalid_arguments", "Invalid launch arguments.", 422) from None
    raise AppError("not_a_launch", "This tool does not launch a playable workflow.", 422)


@dataclass(frozen=True)
class PlayLauncher:
    registry: Registry
    routes: RouteIndex
    send: Callable[[McpIdentity, ToolRequest], Awaitable[InternalResponse]]

    async def __call__(
        self, identity: McpIdentity, launch: str, arguments: dict[str, Any], client: PlayClient
    ) -> dict[str, Any]:
        request, graph = launch_request(self.registry, self.routes, identity, launch, arguments)
        play = PlayContext(identity.user_id, client, graph)
        flag = PLAY_CONTEXT.set(play)
        try:
            response = await self.send(identity, request)
        finally:
            PLAY_CONTEXT.reset(flag)
        if response.status >= 400:
            error = (response.data or {}).get("error", {})
            raise AppError(
                error.get("code", "play_launch_failed"),
                error.get("message", "Lancement impossible."),
                response.status,
                error.get("details"),
            )
        if not play.started:
            raise AppError(
                "play_not_started", "The route did not create a new played session.", 409
            )
        return {"session_id": play.started[0]}
