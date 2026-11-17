"""Quelle route de l'application répond à `méthode chemin` ? (phase 10, P13) : l'index des routes
de l'OpenAPI, dans l'ordre où l'application les déclare (celui que suit le routeur : la première
qui colle gagne). Sert à refuser un identifiant qui, glissé dans un gabarit, tomberait sur une
route sœur statique (`/applications/stats` pour `/applications/{application_id}`)."""

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
    """Les routes de l'OpenAPI, par méthode, dans l'ordre de déclaration."""

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
        """Le gabarit (sans `/api/v1`) de la première route qui répond, sinon `None`."""
        for pattern, template in self._by_method.get(method.upper(), ()):
            if pattern.fullmatch(path):
                return template
        return None

    def ensure_declared(self, tool: ToolSpec, request: ToolRequest) -> None:
        """La requête construite (et sa lecture de base, `merge_from`) tombe sur la route déclarée
        par l'outil, jamais sur une route sœur : sinon `ArgumentError`."""
        if tool.route is None or tool.plan is None:
            return
        self._ensure(request.method, request.path, tool.route[1])
        if request.merge_path is not None and tool.plan.merge_path is not None:
            self._ensure("GET", request.merge_path, tool.plan.merge_path)

    def _ensure(self, method: str, path: str, template: str) -> None:
        found = self.resolve(method, path)
        if found is not None and found != template:
            raise ArgumentError("Argument invalide : cet identifiant désigne une autre route.")
