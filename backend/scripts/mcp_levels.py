"""La table des niveaux MCP (phase 10, 10.D1) : pour chaque feature, ce que Claude peut faire
(outil, niveau, route, effets), les graphes qu'il peut lancer et ce qui est exclu, avec le motif.
Imprimée par `python -m scripts.mcp_levels`, à relire par January avant de donner un jeton.

Le même module énumère les routes réelles de `FEATURE_ROUTERS` (`iter_routes`) : le garde de
couverture (`tests/mcp/test_coverage_guard.py`) s'en sert, jamais d'une liste écrite de mémoire."""

import inspect
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from fastapi import APIRouter
from fastapi.routing import APIRoute, APIWebSocketRoute, _IncludedRouter
from starlette.responses import JSONResponse

from app.mcp.base import FeatureMcp

NO_CONTENT = 204


@dataclass(frozen=True)
class RouteInfo:
    """Une route réelle : `key` = `"POST /postings"` (méthode et chemin sans `/api/v1`),
    `"WS /sessions/{session_id}/stream"` pour un WebSocket."""

    feature: str
    method: str
    path: str
    name: str
    upload: bool  # un champ `UploadFile`
    binary: bool  # réponse qui n'est pas du JSON (fichier, image, archive, redirection)

    @property
    def key(self) -> str:
        return f"{self.method} {self.path}"


def _walk(router: APIRouter, prefix: str = "") -> Iterator[tuple[str, object]]:
    """Les routes d'un routeur, sous-routeurs inclus (`include_router`), avec leur préfixe."""
    for route in router.routes:
        if isinstance(route, _IncludedRouter):
            yield from _walk(route.original_router, prefix + route.include_context.prefix)
        else:
            yield prefix, route


def _feature_of(endpoint: object) -> str:
    module = str(getattr(endpoint, "__module__", ""))
    parts = module.split(".")
    if parts[:2] != ["app", "features"] or len(parts) < 3:
        raise ValueError(f"route hors de `app.features` : {module}")
    return parts[2]


def _is_binary(route: APIRoute) -> bool:
    """Une réponse qui n'est pas du JSON : fichier, image, PDF, archive, redirection. Une réponse
    vide (204) n'en est pas une."""
    response_class = getattr(route.response_class, "value", route.response_class)
    if route.status_code == NO_CONTENT:
        return False
    return not (isinstance(response_class, type) and issubclass(response_class, JSONResponse))


def _has_upload(route: APIRoute) -> bool:
    params = inspect.signature(route.endpoint).parameters.values()
    return any("UploadFile" in str(p.annotation) for p in params)


def iter_routes(routers: Iterable[APIRouter]) -> list[RouteInfo]:
    """Toutes les routes (HEAD et OPTIONS exclus), WebSocket compris, dans l'ordre des routeurs."""
    found: list[RouteInfo] = []
    for router in routers:
        for prefix, route in _walk(router):
            if isinstance(route, APIRoute):
                for method in sorted((route.methods or set()) - {"HEAD", "OPTIONS"}):
                    found.append(
                        RouteInfo(
                            _feature_of(route.endpoint),
                            method,
                            prefix + route.path,
                            route.name,
                            _has_upload(route),
                            _is_binary(route),
                        )
                    )
            elif isinstance(route, APIWebSocketRoute):
                path = prefix + route.path
                found.append(
                    RouteInfo(_feature_of(route.endpoint), "WS", path, route.name, False, True)
                )
    return found


def _effects(action_effects: str, has_precheck: bool) -> str:
    marks = ["externe"] if action_effects == "external" else []
    if has_precheck:
        marks.append("contrôle préalable")
    return ", ".join(marks)


def render_table(features: Iterable[FeatureMcp]) -> str:
    """Trois sections (outils, graphes, exclusions), triées par feature puis par route."""
    ordered = sorted(features, key=lambda f: f.feature)
    tools = ["== Outils (feature | niveau | outil | route | effets)"]
    graphs = ["== Graphes (feature | niveau | graphe | lancement)"]
    launched_by: dict[str, list[str]] = {}
    for feature in ordered:
        for action in feature.actions:
            if action.launches is not None:
                launched_by.setdefault(action.launches, []).append(action.route)
    excluded = ["== Exclus (feature | route | motif)"]
    for feature in ordered:
        for action in sorted(feature.actions, key=lambda a: a.route):
            effects = _effects(action.side_effects, action.precheck is not None)
            tools.append(
                f"{feature.feature} | {action.level} | {action.name} | {action.route} | {effects}"
            )
        for graph in sorted(feature.graphs, key=lambda g: g.graph):
            routes = " ou ".join(sorted(launched_by.get(graph.graph, []))) or "l'interface"
            launch = (
                f"suivi seulement, lancé par {routes}"
                if graph.follow_only
                else f"outil graph_{graph.graph}"
            )
            graphs.append(f"{feature.feature} | {graph.level} | {graph.graph} | {launch}")
        for key, reason in sorted(feature.excluded.items()):
            excluded.append(f"{feature.feature} | {key} | {reason}")
    return "\n".join([*tools, "", *graphs, "", *excluded])


def main() -> None:
    from app.features.registry import MCP_FEATURES

    print(render_table(MCP_FEATURES))


if __name__ == "__main__":
    main()
