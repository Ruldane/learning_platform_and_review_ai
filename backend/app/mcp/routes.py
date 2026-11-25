"""Which application route answers `method path`? (phase 10, P13): the index of the OpenAPI routes,
in the order the application declares them (the one the router follows: the first match wins).
Used to refuse an identifier that, slipped into a template, would land on a static sibling route
(`/applications/stats` for `/applications/{application_id}`)."""

import re
from collections.abc import Mapping
from typing import Any

from app.mcp.arguments import ArgumentError, ToolRequest
from app.mcp.schema import API_PREFIX
from app.mcp.tools import ToolSpec

_PLACEHOLDER = re.compile(r"(\{[^}/]+\})")


def _pattern(template: str) -> re.Pattern[str]:
    parts = _PLACEHOLDER.split(template)
    pieces = ("[^/]+" if part.startswith("{") else re.escape(part) for part in parts)
    return re.compile("".join(pieces))


class RouteIndex:
    """The OpenAPI routes, by method, in declaration order."""

    def __init__(self, openapi: Mapping[str, Any]) -> None:
        self._by_method: dict[str, list[tuple[re.Pattern[str], str]]] = {}
        for path, operations in openapi.get("paths", {}).items():
            if not path.startswith(API_PREFIX + "/"):
                continue
            template = path.removeprefix(API_PREFIX)
            pattern = _pattern(template)
            for method in operations:
                self._by_method.setdefault(method.upper(), []).append((pattern, template))

    def resolve(self, method: str, path: str) -> str | None:
        """The template (without `/api/v1`) of the first route that answers, otherwise `None`."""
        for pattern, template in self._by_method.get(method.upper(), ()):
            if pattern.fullmatch(path):
                return template
        return None

    def ensure_declared(self, tool: ToolSpec, request: ToolRequest) -> None:
        """The built request (and its base read, `merge_from`) lands on the route declared
        by the tool, never on a sibling route; otherwise `ArgumentError`."""
        if tool.route is None or tool.plan is None:
            return
        self._ensure(request.method, request.path, tool.route[1])
        if request.merge_path is not None and tool.plan.merge_path is not None:
            self._ensure("GET", request.merge_path, tool.plan.merge_path)

    def _ensure(self, method: str, path: str, template: str) -> None:
        found = self.resolve(method, path)
        if found is not None and found != template:
            raise ArgumentError("Invalid argument: this identifier points to another route.")
