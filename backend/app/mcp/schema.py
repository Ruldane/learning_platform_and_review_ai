"""Du contrat OpenAPI d'une route à l'outil MCP (phase 10, P13) et retour : le schéma d'entrée d'un
outil (chemin, requête et corps fusionnés en un objet plat ; collision de nom : préfixe `body_`), le
plan qui range chaque argument à sa place (les arguments d'un appel : `app/mcp/arguments.py`).

Rien n'est deviné : tout vient de l'OpenAPI de l'application. Une déclaration qui ne colle pas à une
vraie route (route absente, champ inconnu, route de fichier) est une `McpConfigError`, levée au
démarrage."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

API_PREFIX = "/api/v1"
# Routes que le MCP n'atteint jamais, quelle que soit la déclaration (niveau 4) : connexion,
# compte et ses données, le MCP lui-même, clés d'API, modèles par niveau, surcharges par agent.
NEVER_REACHABLE = (
    "/auth",
    "/account",
    "/calendar",
    "/brain/folders",
    "/brain/sync",
    "/brain/sync-token",
    "/ide/terminals",
    "/ide/notebook-runs",
    "/mcp",
    "/settings/api-keys",
    "/settings/models",
    "/settings/agents",
)
CALENDAR_MCP_PATHS = frozenset({"/calendar/upcoming", "/calendar/proposals"})
SETTINGS_PATH = "/settings"
_FORM_MEDIA = ("multipart/form-data", "application/x-www-form-urlencoded")


class McpConfigError(ValueError):
    """Une déclaration qui ne colle pas à l'application : le démarrage échoue."""


@dataclass(frozen=True)
class RoutePlan:
    """Où va chaque argument d'un outil de route : chemin, requête ou corps. `body_args` : nom de
    l'argument -> clé du corps ; `body_whole` : l'argument qui est tout le corps (corps non objet) ;
    `merge_path` : gabarit de la route GET dont la réponse sert de base au corps (`merge_from`)."""

    method: str
    path: str
    path_params: frozenset[str]
    query_params: frozenset[str]
    body_args: Mapping[str, str]
    body_whole: str | None
    has_body: bool
    form: bool
    merge_path: str | None = None
    merge_fields: frozenset[str] | None = None


def never_reachable(path: str) -> bool:
    if path in CALENDAR_MCP_PATHS:
        return False
    return any(path == base or path.startswith(base + "/") for base in NEVER_REACHABLE)


def _resolve(node: Mapping[str, Any], components: Mapping[str, Any]) -> Mapping[str, Any]:
    """Suit un `$ref` (ou un `allOf` d'un seul élément) jusqu'au schéma réel."""
    for _ in range(8):
        if "$ref" in node:
            node = components[node["$ref"].rsplit("/", 1)[1]]
        elif len(node.get("allOf", ())) == 1:
            node = node["allOf"][0]
        else:
            break
    return node


def _port(node: Any, components: Mapping[str, Any], defs: dict[str, Any]) -> Any:
    """Copie un schéma OpenAPI en JSON Schema autonome : chaque `$ref` des composants devient un
    `$defs` local (les références circulaires s'arrêtent à la première visite)."""
    if isinstance(node, dict):
        out: dict[str, Any] = {}
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str) and value.startswith("#/components/"):
                name = value.rsplit("/", 1)[1]
                if name not in defs:
                    defs[name] = {}
                    defs[name] = _port(components[name], components, defs)
                out["$ref"] = f"#/$defs/{name}"
            else:
                out[key] = _port(value, components, defs)
        return out
    if isinstance(node, list):
        return [_port(item, components, defs) for item in node]
    return node


def _is_file(node: Mapping[str, Any], components: Mapping[str, Any]) -> bool:
    node = _resolve(node, components)
    options = [*node.get("anyOf", ()), *node.get("oneOf", ())]
    if any(_is_file(option, components) for option in options):
        return True  # un fichier facultatif : `anyOf: [fichier, null]`
    item = _resolve(node.get("items", {}), components)
    return "binary" in (node.get("format"), item.get("format")) or "contentMediaType" in {
        **node,
        **item,
    }


def operation(openapi: Mapping[str, Any], method: str, path: str) -> Mapping[str, Any]:
    found = openapi.get("paths", {}).get(API_PREFIX + path, {}).get(method.lower())
    if found is None:
        raise McpConfigError(f"route déclarée mais absente de l'application : {method} {path}")
    return found  # type: ignore[no-any-return]


def split_route(route: str) -> tuple[str, str]:
    method, _, path = route.partition(" ")
    if method not in ("GET", "POST", "PUT", "PATCH", "DELETE") or not path.startswith("/"):
        raise McpConfigError(f"route mal formée : « {route} » (attendu « POST /postings »)")
    return method, path


def describe(op: Mapping[str, Any], summary: str | None) -> str:
    """Le résumé de la route : celui de la déclaration, sinon la première ligne de la docstring."""
    if summary:
        return summary
    doc = str(op.get("description") or "").strip().splitlines()
    return (doc[0] if doc else str(op.get("summary") or "")).strip()[:300]


def _body_media(op: Mapping[str, Any], form: bool, route: str) -> Mapping[str, Any] | None:
    body = op.get("requestBody")
    if body is None:
        return None
    content = body.get("content", {})
    wanted = _FORM_MEDIA if form else ("application/json",)
    for media in wanted:
        if media in content:
            return {"schema": content[media].get("schema", {}), "required": body.get("required")}
    hint = "un formulaire sans fichier" if form else 'du JSON (formulaire : encoding="form")'
    raise McpConfigError(f"{route} ne reçoit pas {hint} : corriger la déclaration ou exclure")


def _parameters(
    op: Mapping[str, Any], components: Mapping[str, Any], defs: dict[str, Any]
) -> tuple[dict[str, Any], list[str], set[str], set[str]]:
    """Les paramètres de chemin et de requête d'une opération (les en-têtes et cookies sont
    ignorés) : leurs schémas, ceux qui sont obligatoires, et les deux ensembles de noms."""
    props: dict[str, Any] = {}
    required: list[str] = []
    path_params: set[str] = set()
    query_params: set[str] = set()
    for param in op.get("parameters", []):
        where, name = param.get("in"), param["name"]
        if where not in ("path", "query"):
            continue
        (path_params if where == "path" else query_params).add(name)
        props[name] = _port(param.get("schema", {}), components, defs)
        if param.get("required") or where == "path":
            required.append(name)
    return props, required, path_params, query_params


def build_route_tool(
    openapi: Mapping[str, Any],
    route: str,
    *,
    body_fields: frozenset[str] | None,
    merge_from: str | None,
    encoding: Literal["json", "form"],
) -> tuple[dict[str, Any], RoutePlan, Mapping[str, Any]]:
    """`(schéma d'entrée, plan, opération OpenAPI)` d'une route déclarée."""
    method, path = split_route(route)
    op = operation(openapi, method, path)
    components: Mapping[str, Any] = openapi.get("components", {}).get("schemas", {})
    defs: dict[str, Any] = {}
    props, required, path_params, query_params = _parameters(op, components, defs)
    body_args: dict[str, str] = {}
    whole: str | None = None
    media = _body_media(op, encoding == "form", route)
    if media is not None:
        whole = _body_arguments(
            media, components, defs, props, required, body_args, body_fields, merge_from, route
        )
    elif body_fields is not None:
        raise McpConfigError(f"{route} : body_fields sans corps de requête")
    merge_path = _merge_path(openapi, route, path_params, merge_from, body_fields)
    schema: dict[str, Any] = {"type": "object", "properties": props, "additionalProperties": False}
    if required:
        schema["required"] = required
    if defs:
        schema["$defs"] = defs
    plan = RoutePlan(
        method=method,
        path=path,
        path_params=frozenset(path_params),
        query_params=frozenset(query_params),
        body_args=body_args,
        body_whole=whole,
        has_body=media is not None,
        form=encoding == "form",
        merge_path=merge_path,
        merge_fields=body_fields if merge_path else None,
    )
    return schema, plan, op


def _body_arguments(
    media: Mapping[str, Any],
    components: Mapping[str, Any],
    defs: dict[str, Any],
    props: dict[str, Any],
    required: list[str],
    body_args: dict[str, str],
    allowed: frozenset[str] | None,
    merge_from: str | None,
    route: str,
) -> str | None:
    """Les champs du corps deviennent des arguments plats (liste blanche `allowed` si donnée) ;
    rend le nom de l'argument « corps entier » pour un corps qui n'est pas un objet à champs."""
    schema = _resolve(media["schema"], components)
    fields: Mapping[str, Any] = schema.get("properties", {})
    if not fields:
        if allowed is not None:
            raise McpConfigError(f"{route} : body_fields sans champs de corps")
        props["body"] = _port(schema, components, defs)
        if media["required"]:
            required.append("body")
        return "body"
    unknown = (allowed or frozenset()) - fields.keys()
    if unknown:
        raise McpConfigError(f"{route} : champs de corps inconnus {sorted(unknown)}")
    needed = set(schema.get("required", ()))
    for key, sub in fields.items():
        if allowed is not None and key not in allowed:
            continue
        if _is_file(sub, components):
            if key in needed:
                raise McpConfigError(f"{route} : le champ « {key} » est un fichier (non exposé)")
            continue
        name = key if key not in props else f"body_{key}"
        props[name] = _port(sub, components, defs)
        body_args[name] = key
        if key in needed and merge_from is None:
            required.append(name)
    return None


def _merge_path(
    openapi: Mapping[str, Any],
    route: str,
    path_params: set[str],
    merge_from: str | None,
    body_fields: frozenset[str] | None,
) -> str | None:
    if merge_from is None:
        return None
    method, path = split_route(merge_from)
    if method != "GET" or body_fields is None:
        raise McpConfigError(f"{route} : merge_from est une route GET et exige body_fields")
    operation(openapi, method, path)
    needed = {part[1:-1] for part in path.split("/") if part.startswith("{")}
    if not needed <= path_params:
        raise McpConfigError(f"{route} : {merge_from} demande des paramètres que la route n'a pas")
    return path
