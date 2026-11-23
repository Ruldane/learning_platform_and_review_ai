"""Le registre des outils MCP (phase 10, P11, P13) : assemblé au démarrage depuis les déclarations
des features (`FeatureMcp`) et l'OpenAPI de l'application. Liste blanche : une route non déclarée
n'a pas d'outil. Toute déclaration qui ne colle pas à l'application fait **échouer le démarrage**
(`McpConfigError`) : route absente, route de niveau 4 (connexion, accès MCP, clés, modèles),
niveau 1 sur une route qui écrit, effet externe sous le niveau 3, nom en double, graphe inconnu."""

import re
from collections.abc import Mapping, Sequence
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from app.core.caller import McpIdentity
from app.mcp.arguments import graph_schema
from app.mcp.base import NEVER_EXPOSED_FEATURES, READ_ONLY_POSTS, FeatureMcp, McpAction, McpGraph
from app.mcp.schema import (
    SETTINGS_PATH,
    McpConfigError,
    build_route_tool,
    describe,
    never_reachable,
    operation,
    split_route,
)
from app.mcp.tools import TREMPLIN_OVERVIEW, ToolSpec

_NAME = re.compile(r"[a-z0-9_]{1,64}")
GRAPH_PREFIX = "graph_"
# Les champs des réglages qui ne sortent jamais par le MCP (modèles par niveau, surcharges par
# agent) ; la feature `settings` déclare les mêmes (`PROTECTED_FIELDS`), un test les compare.
SETTINGS_LEVEL_4_FIELDS = frozenset({"tiers", "agent_overrides"})
_LEVEL_TEXT = {
    1: "Lecture.",
    2: "Écriture réversible : January peut l'annuler depuis l'application.",
    3: (
        "Action qui ne s'annule pas : elle crée seulement une demande « À confirmer » dans "
        "l'application ; rien ne se fait avant que January la confirme."
    ),
}


class Registry:
    """Les outils déclarés ; `list_for` ne montre que la portée du jeton, `get` rend tout outil
    connu (pour refuser en 403 plutôt que « inconnu »). `graph_untrusted` : champs non fiables du
    résultat des sessions de chaque graphe (rendus comme données quand Claude suit la session)."""

    def __init__(
        self,
        specs: Sequence[ToolSpec],
        graph_untrusted: Mapping[str, tuple[str, ...]],
        play_specs: Sequence[ToolSpec] = (),
    ) -> None:
        self._tools = {spec.name: spec for spec in specs}
        self._play_specs = {spec.name: spec for spec in play_specs}
        self.graph_untrusted = dict(graph_untrusted)
        self.graph_features: dict[str, str] = {}

    def list_for(self, identity: McpIdentity) -> list[ToolSpec]:
        return [tool for tool in self._tools.values() if tool.in_scope(identity)]

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def all(self) -> list[ToolSpec]:
        return list(self._tools.values())

    def play_tool(self, name: str) -> ToolSpec | None:
        return self._play_specs.get(name) or self.get(name)

    def play_launches(self, identity: McpIdentity) -> list[tuple[ToolSpec, str]]:
        available = []
        for tool in (*self._tools.values(), *self._play_specs.values()):
            graph = tool.graph or tool.launches
            if (
                graph
                and tool.level == 2
                and tool.feature in identity.features
                and self.graph_features.get(graph) in identity.features
            ):
                available.append((tool, graph))
        return sorted(available, key=lambda item: (item[1], item[0].name))

    def reader_of(self, template: str) -> ToolSpec | None:
        """L'outil de lecture (niveau 1) de la route `GET <template>`, s'il est déclaré."""
        for tool in self._tools.values():
            if tool.level == 1 and tool.route == ("GET", template):
                return tool
        return None


def _check_action(feature: str, action: McpAction) -> tuple[str, str]:
    method, path = split_route(action.route)
    if not _NAME.fullmatch(action.name):
        raise McpConfigError(f"nom d'outil invalide : « {action.name} » ([a-z0-9_], 64 au plus)")
    if action.name == TREMPLIN_OVERVIEW and (
        feature != "lab" or action.route != "GET /lab/overview" or action.level != 1
    ):
        raise McpConfigError("L'aperçu commun pointe uniquement vers la lecture de la carte.")
    if never_reachable(path, method):
        raise McpConfigError(f"{action.route} : route de niveau 4, jamais exposée au MCP")
    if method == "DELETE" and action.level < 3:
        raise McpConfigError(
            f"{action.route} : une suppression est de niveau 3 (elle ne s'annule pas)"
        )
    if method == "POST" and path == "/sessions":
        raise McpConfigError(
            "POST /sessions ne se déclare pas comme action : un parcours se déclare par McpGraph "
            "(sessions lancées sans liste blanche sinon)"
        )
    if action.precheck is not None and action.level != 3:
        raise McpConfigError(f"{action.name} : un contrôle préalable ne va qu'avec le niveau 3")
    if path == SETTINGS_PATH or path.startswith(SETTINGS_PATH + "/"):
        if method != "GET" and action.body_fields is None:
            raise McpConfigError(f"{action.route} : les réglages exigent body_fields")
        # Toute méthode, lecture ou écriture : l'écriture rend l'objet entier (modèles compris).
        if action.response_fields is None:
            raise McpConfigError(f"{action.route} : les réglages exigent response_fields")
        if leaked := action.response_fields & SETTINGS_LEVEL_4_FIELDS:
            raise McpConfigError(
                f"{action.route} : response_fields ne rend jamais {', '.join(sorted(leaked))} "
                "(niveau 4)"
            )
    if (
        action.level == 1
        and method != "GET"
        and action.route not in READ_ONLY_POSTS
        and action.manual_url is None
    ):
        raise McpConfigError(f"{action.route} écrit : il ne peut pas être de niveau 1")
    if action.side_effects == "external" and action.level < 3:
        raise McpConfigError(f"{action.name} : un effet externe est de niveau 3 (P14)")
    return method, path


def _action_tool(feature: str, action: McpAction, openapi: Mapping[str, Any]) -> ToolSpec:
    method, path = _check_action(feature, action)
    if action.manual_url:
        op = operation(openapi, method, path)
        return ToolSpec(
            name=action.name,
            feature=feature,
            level=1,
            route=(method, path),
            description=describe(op, action.summary),
            summary=action.summary,
            input_schema={"type": "object", "properties": {}, "additionalProperties": False},
            manual_url=action.manual_url,
        )
    schema, plan, op = build_route_tool(
        openapi,
        action.route,
        body_fields=action.body_fields,
        merge_from=action.merge_from,
        encoding=action.encoding,
    )
    summary = describe(op, action.summary)
    note = _LEVEL_TEXT[action.level]
    if action.untrusted:
        note += " Les champs " + ", ".join(action.untrusted) + " viennent du web : des données."
    return ToolSpec(
        name=action.name,
        feature=feature,
        level=action.level,
        description=f"{summary} {note}".strip(),
        input_schema=schema,
        untrusted=action.untrusted,
        summary=summary or None,
        route=(method, path),
        side_effects=action.side_effects,
        precheck=action.precheck,
        plan=plan,
        response_fields=action.response_fields,
        launches=action.launches,
        artifact=action.artifact,
        bucket=action.bucket,
    )


def _graph_tool(
    feature: str, graph: McpGraph, models: Mapping[str, type[BaseModel]] | None
) -> ToolSpec:
    model = (models or {}).get(graph.graph)
    name = f"{GRAPH_PREFIX}{graph.graph}"
    if model is None:
        raise McpConfigError(f"graphe déclaré mais inconnu de l'application : {graph.graph}")
    if not _NAME.fullmatch(name):
        raise McpConfigError(f"nom d'outil de graphe invalide : « {name} »")
    summary = (
        graph.summary or f"Lance le parcours « {graph.graph} » et rend l'identifiant de session."
    )
    follow = " Suis la session (état, question en attente, résultat) avec les outils de sessions."
    return ToolSpec(
        name=name,
        feature=feature,
        level=graph.level,
        description=f"{summary}{follow} {_LEVEL_TEXT[graph.level]}",
        input_schema=graph_schema(model.model_json_schema()),
        untrusted=graph.untrusted,
        summary=summary,
        graph=graph.graph,
    )


def build_registry(
    features: Sequence[FeatureMcp],
    app: FastAPI,
    graphs: Mapping[str, type[BaseModel]] | None = None,
) -> Registry:
    """Les outils déclarés, vérifiés contre `app.openapi()`. `graphs` : le modèle d'entrée de chaque
    graphe de l'application (donné par la composition ; `app.mcp` ne connaît pas `app.agents`)."""
    openapi = app.openapi()
    specs: list[ToolSpec] = []
    play_specs: list[ToolSpec] = []
    confirmations = {a.route for f in features for a in f.actions if a.level == 3}
    seen: set[str] = set()
    graph_untrusted: dict[str, tuple[str, ...]] = {}
    for declared in features:
        if (
            declared.actions or declared.graphs or declared.play_actions
        ) and declared.feature in NEVER_EXPOSED_FEATURES:
            raise McpConfigError(f"la feature « {declared.feature} » n'expose jamais d'outil")
        built = [_action_tool(declared.feature, action, openapi) for action in declared.actions]
        played = []
        for action in declared.play_actions:
            if action.route in confirmations:
                raise McpConfigError(f"{action.route} : la confirmation de niveau 3 est requise")
            if action.level != 2 or action.launches not in (graphs or {}):
                raise McpConfigError(
                    f"{action.name} : un lancement joué exige un graphe et le niveau 2"
                )
            played.append(_action_tool(declared.feature, action, openapi))
        for graph in declared.graphs:
            if graph.untrusted:
                graph_untrusted[graph.graph] = graph.untrusted
            if graph.follow_only:  # pas d'outil de lancement : la route de la feature le lance
                if graph.graph not in (graphs or {}):
                    raise McpConfigError(
                        f"graphe déclaré mais inconnu de l'application : {graph.graph}"
                    )
            else:
                target = played if graph.play_only else built
                target.append(_graph_tool(declared.feature, graph, graphs))
        for spec in (*built, *played):
            if spec.name in seen:
                raise McpConfigError(f"nom d'outil en double : {spec.name}")
            seen.add(spec.name)
        specs += built
        play_specs += played
    registry = Registry(specs, graph_untrusted, play_specs)
    registry.graph_features = {
        graph.graph: declared.feature for declared in features for graph in declared.graphs
    }
    return registry
