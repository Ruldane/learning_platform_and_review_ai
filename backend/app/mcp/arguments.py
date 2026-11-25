"""Arguments of an MCP tool (phase 10, P13): checked against the tool's schema and arranged into a
request (`build_request`). An unknown, missing or malformed argument is a readable
`ArgumentError` that never quotes the values received; a path parameter is an identifier,
never a way out of the route's template."""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from app.mcp.schema import RoutePlan

_MAX_ECHO = 40
_PLACEHOLDER = re.compile(r"\{([A-Za-z0-9_]+)\}")


class ArgumentError(Exception):
    """Refused tool arguments (`fields`: their names, never their values)."""

    def __init__(self, message: str, fields: list[str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.fields = fields or []


@dataclass(frozen=True)
class ToolRequest:
    """The internal request of a tool call, ready to go (path without `/api/v1`)."""

    method: str
    path: str
    params: dict[str, Any]
    body: Any
    form: bool = False
    merge_path: str | None = None
    merge_fields: tuple[str, ...] | None = None


def clip(text: object, size: int = _MAX_ECHO) -> str:
    """A received name, made harmless for a message: printable, truncated."""
    cleaned = "".join(ch if ch.isprintable() else " " for ch in str(text))
    return cleaned if len(cleaned) <= size else cleaned[:size] + "…"


def check_arguments(schema: Mapping[str, Any], arguments: Mapping[str, Any]) -> None:
    """Unknown or missing argument: `ArgumentError`, without quoting the values."""
    known = schema.get("properties", {})
    unknown = [name for name in arguments if name not in known]
    if unknown:
        listed = ", ".join(clip(name) for name in unknown[:5])
        raise ArgumentError(f"Unknown argument: {listed}. Read the tool's inputSchema.", unknown)
    missing = [name for name in schema.get("required", ()) if name not in arguments]
    if missing:
        raise ArgumentError(f"Missing argument: {', '.join(missing)}.", missing)


def _segment(name: str, value: Any) -> str:
    """A path parameter: an identifier, never a way out of the route's template."""
    ok_type = isinstance(value, str | int) and not isinstance(value, bool)
    text = str(value) if ok_type else ""
    bad = not text or text in (".", "..") or len(text) > 200
    bad = bad or any(ch in "/\\?#%{}" or not ch.isprintable() or ch.isspace() for ch in text)
    if bad:
        raise ArgumentError(f'Invalid argument "{name}": an identifier, without / or ..', [name])
    return text


def _query_value(name: str, value: Any) -> Any:
    scalar = (str, int, float, bool)
    if isinstance(value, scalar) or (
        isinstance(value, list) and all(isinstance(item, scalar) for item in value)
    ):
        return value
    raise ArgumentError(f'Invalid argument "{name}": a text, a number or a list.', [name])


def _fill(template: str, segments: Mapping[str, str]) -> str:
    """Fills the template in a single pass: a value is never read again as a `{name}`."""
    return _PLACEHOLDER.sub(lambda found: segments.get(found.group(1), found.group(0)), template)


def build_request(plan: RoutePlan, arguments: Mapping[str, Any]) -> ToolRequest:
    """Arranges the arguments (already checked by `check_arguments`): path, query, body."""
    segments: dict[str, str] = {}
    params: dict[str, Any] = {}
    body: dict[str, Any] = {}
    whole: Any = None
    for name, value in arguments.items():
        if name in plan.path_params:
            segments[name] = _segment(name, value)
        elif name in plan.query_params:
            if value is not None:
                params[name] = _query_value(name, value)
        elif name in plan.body_args:
            body[plan.body_args[name]] = value
        elif name == plan.body_whole:
            whole = value
    path = _fill(plan.path, segments)
    merge = _fill(plan.merge_path, segments) if plan.merge_path else None
    payload: Any = None
    if plan.has_body:
        payload = whole if plan.body_whole else body
    fields = tuple(sorted(plan.merge_fields)) if plan.merge_fields else None
    return ToolRequest(plan.method, path, params, payload, plan.form, merge, fields)


def graph_schema(model_schema: Mapping[str, Any]) -> dict[str, Any]:
    """The input schema of a graph tool: the fields of its `input_model`, flat."""
    schema: dict[str, Any] = {
        "type": "object",
        "properties": dict(model_schema.get("properties", {})),
        "additionalProperties": False,
    }
    if model_schema.get("required"):
        schema["required"] = list(model_schema["required"])
    if model_schema.get("$defs"):
        schema["$defs"] = dict(model_schema["$defs"])
    return schema
