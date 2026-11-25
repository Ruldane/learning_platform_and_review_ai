"""From a route's OpenAPI contract to an MCP tool, and back: a tool's input schema (path, query and
body merged into a flat object; name collision: `body_` prefix), and the plan that puts each
argument in its place (the arguments of a call: `app/mcp/arguments.py`).

Nothing is guessed: everything comes from the application's OpenAPI. A declaration that does not
match a real route (missing route, unknown field, file route) is an `McpConfigError`, raised at
startup."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

API_PREFIX = "/api/v1"
# Sensitive spaces. Only the method and path pairs of _SCOPED_ACCESS open them.
NEVER_REACHABLE = (
    "/auth",
    "/account",
    "/calendar/callback",
    "/brain/sync",
    "/brain/sync-token",
    "/mcp",
    "/settings/api-keys",
    "/settings/models",
    "/settings/agents",
    "/mentor-reviews/shared",
    "/message-reviews/settings",
    "/surprise-interviews/settings",
)
_SCOPED_ACCESS = frozenset(
    {
        ("GET", "/account/export"),
        ("POST", "/account/delete"),
        ("GET", "/calendar/connection"),
        ("DELETE", "/calendar/connection"),
        ("GET", "/ide/preferences"),
        ("GET", "/mentor-reviews/shares"),
    }
)
_PROTECTED = frozenset({"/calendar/connection", "/ide/preferences", "/mentor-reviews/shares"})
SETTINGS_PATH = "/settings"
_FORM_MEDIA = ("multipart/form-data", "application/x-www-form-urlencoded")


class McpConfigError(ValueError):
    """A declaration that does not match the application: startup fails."""


@dataclass(frozen=True)
class RoutePlan:
    """Where each argument of a route tool goes: path, query or body. `body_args`: argument name ->
    body key; `body_whole`: the argument that is the whole body (non-object body); `merge_path`:
    template of the GET route whose response is the base of the body (`merge_from`)."""

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


def never_reachable(path: str, method: str | None = None) -> bool:
    if (method, path) in _SCOPED_ACCESS:
        return False
    if path in _PROTECTED:
        return True
    return any(path == base or path.startswith(base + "/") for base in NEVER_REACHABLE)


def _resolve(node: Mapping[str, Any], components: Mapping[str, Any]) -> Mapping[str, Any]:
    """Follows a `$ref` (or an `allOf` with a single element) to the actual schema."""
    for _ in range(8):
        if "$ref" in node:
            node = components[node["$ref"].rsplit("/", 1)[1]]
        elif len(node.get("allOf", ())) == 1:
            node = node["allOf"][0]
        else:
            break
    return node


def _port(node: Any, components: Mapping[str, Any], defs: dict[str, Any]) -> Any:
    """Copies an OpenAPI schema into a standalone JSON Schema: each `$ref` of the components becomes
    a
    local `$defs` (circular references stop at the first visit)."""
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
        raise McpConfigError(f"route declared but missing from the app: {method} {path}")
    return found  # type: ignore[no-any-return]


def split_route(route: str) -> tuple[str, str]:
    method, _, path = route.partition(" ")
    if method not in ("GET", "POST", "PUT", "PATCH", "DELETE") or not path.startswith("/"):
        raise McpConfigError(f"malformed route '{route}' (expected 'POST /postings')")
    return method, path


def describe(op: Mapping[str, Any], summary: str | None) -> str:
    """The route's summary: the declaration's one, otherwise the first line of the docstring."""
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
    hint = "a form without a file" if form else 'JSON (form: encoding="form")'
    raise McpConfigError(f"{route} does not accept {hint}: fix the declaration or exclude it")


def _parameters(
    op: Mapping[str, Any], components: Mapping[str, Any], defs: dict[str, Any]
) -> tuple[dict[str, Any], list[str], set[str], set[str]]:
    """The path and query parameters of an operation (headers and cookies are ignored): their
    schemas,
    which ones are required, and the two sets of names."""
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
    """`(input schema, plan, OpenAPI operation)` of a declared route."""
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
        raise McpConfigError(f"{route}: body_fields without a request body")
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
    """Body fields become flat arguments (allowlist `allowed` if given); returns the name of the
    "whole body" argument for a body that is not an object with fields."""
    schema = _resolve(media["schema"], components)
    fields: Mapping[str, Any] = schema.get("properties", {})
    if not fields:
        if allowed is not None:
            raise McpConfigError(f"{route}: body_fields without body fields")
        props["body"] = _port(schema, components, defs)
        if media["required"]:
            required.append("body")
        return "body"
    unknown = (allowed or frozenset()) - fields.keys()
    if unknown:
        raise McpConfigError(f"{route}: unknown body fields {sorted(unknown)}")
    needed = set(schema.get("required", ()))
    for key, sub in fields.items():
        if allowed is not None and key not in allowed:
            continue
        if _is_file(sub, components):
            if key in needed:
                raise McpConfigError(f"{route}: the field '{key}' is a file (not exposed)")
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
        raise McpConfigError(f"{route}: merge_from is a GET route and requires body_fields")
    operation(openapi, method, path)
    needed = {part[1:-1] for part in path.split("/") if part.startswith("{")}
    if not needed <= path_params:
        raise McpConfigError(f"{route}: {merge_from} needs parameters the route does not have")
    return path
