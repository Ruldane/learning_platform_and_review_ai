"""Public validation errors derived from the fields declared by the route."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import UnionType
from typing import Annotated, Any, Literal, Union, get_args, get_origin

from fastapi import Request
from fastapi.dependencies.models import Dependant
from fastapi.dependencies.utils import _get_form_models, _get_param_aliases, _get_param_model
from fastapi.routing import APIRoute
from pydantic import AliasChoices, AliasPath, BaseModel, RootModel
from pydantic_core.core_schema import ErrorType

ROOTS = ("body", "query", "path", "header", "cookie")
_TYPES = frozenset(get_args(ErrorType))
_MESSAGES = {
    "missing": "This field is required.",
    "extra_forbidden": "This field is not allowed.",
    "json_invalid": "Invalid JSON body.",
    "int_parsing": "Enter a whole number.",
    "int_type": "Enter a whole number.",
    "string_type": "Enter text.",
    "bool_parsing": "Choose true or false.",
    "bool_type": "Choose true or false.",
    "list_type": "A list is required.",
    "dict_type": "An object is required.",
    "string_too_short": "The text is too short.",
    "string_too_long": "The text is too long.",
    "too_short": "Add more items.",
    "too_long": "Remove some items.",
    "literal_error": "Choose one of the allowed values.",
    "enum": "Choose one of the allowed values.",
}

type Location = tuple[str | int, ...]


@dataclass(frozen=True)
class KnownMappingKeys:
    """Server-defined keys for a dictionary field."""

    keys: frozenset[str]


def _aliases(name: str, alias: str | AliasPath | AliasChoices | None) -> list[Location]:
    choices = alias.choices if isinstance(alias, AliasChoices) else [alias or name]
    return [
        tuple(choice.path) if isinstance(choice, AliasPath) else (choice,) for choice in choices
    ]


def _model_location(model: type[BaseModel], parts: Location) -> Location:
    for name, field in model.model_fields.items():
        if issubclass(model, RootModel):
            return _declared_location(field.rebuild_annotation(), parts)
        for alias in [(name,), *_aliases(name, field.validation_alias)]:
            if parts[: len(alias)] == alias:
                suffix = _declared_location(field.rebuild_annotation(), parts[len(alias) :])
                return (*alias, *suffix)
    return ()


def _union_location(args: tuple[Any, ...], parts: Location) -> Location:
    options: list[Location] = []
    for branch in args:
        if get_origin(branch) is Annotated:
            branch = get_args(branch)[0]
        if (
            len(args) > 1
            and isinstance(branch, type)
            and issubclass(branch, BaseModel)
            and parts[0] == branch.__name__
        ):
            options.append(_declared_location(branch, parts[1:]))
            continue
        options.append(_declared_location(branch, parts))
    return max(options, key=len, default=())


def _declared_location(
    annotation: Any, parts: Location, known_keys: frozenset[str] = frozenset()
) -> Location:
    if not parts:
        return ()
    origin, args = get_origin(annotation), get_args(annotation)
    first, rest = parts[0], parts[1:]
    if origin is Annotated:
        keys = next(
            (item.keys for item in args[1:] if isinstance(item, KnownMappingKeys)), known_keys
        )
        return _declared_location(args[0], parts, keys)
    if origin in (Union, UnionType):
        return _union_location(tuple(arg for arg in args if arg is not type(None)), parts)
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return _model_location(annotation, parts)
    if origin in (dict, Mapping) and len(args) == 2:
        key_type, value_type = args
        allowed = get_args(key_type) if get_origin(key_type) is Literal else ()
        if first in allowed or first in known_keys:
            return (first, *_declared_location(value_type, rest))
    if origin in (list, set, frozenset, tuple, Sequence) and type(first) is int and first >= 0:
        if origin is tuple and args and args[-1] is not Ellipsis:
            return (first, *_declared_location(args[first], rest)) if first < len(args) else ()
        return (first, *_declared_location(args[0], rest)) if args else (first,)
    return ()


def _route_location(route: APIRoute, root: str, parts: Location) -> Location:
    if not parts:
        return ()
    options: list[Location] = []
    pending: list[Dependant] = [route.dependant]
    while pending:
        dependant = pending.pop()
        pending.extend(dependant.dependencies)
        for field in getattr(dependant, f"{root}_params"):
            annotation = field.field_info.rebuild_annotation()
            if root == "body":
                forms = _get_form_models(field)
                if forms:
                    options.append(_union_location(tuple(forms), parts))
                    continue
                if not route._embed_body_fields:
                    options.append(_declared_location(annotation, parts))
                    continue
            elif model := _get_param_model(field):
                options.append(_model_location(model, parts))
                continue
            convert = root == "header" and getattr(field.field_info, "convert_underscores", False)
            names = {name for _, name in _get_param_aliases(field, convert_underscores=convert)}
            if parts[0] in names:
                options.append((parts[0], *_declared_location(annotation, parts[1:])))
    return max(options, key=len, default=())


def validated_location(request: Request, error: Mapping[str, Any]) -> Location:
    """Return the longest path prefix verified against the route's declared fields."""
    loc = error.get("loc")
    if not isinstance(loc, list | tuple) or not loc or loc[0] not in ROOTS:
        return ("body",)
    root, parts = loc[0], tuple(loc[1:])
    if error.get("type") == "json_invalid":
        return ("body",)  # A JSON decoder position is a character offset.
    if error.get("type") == "extra_forbidden":
        parts = parts[:-1]
    if not all(type(part) in (str, int) for part in parts):
        return (root,)
    route = request.scope.get("route")
    if not isinstance(route, APIRoute):
        return (root,)
    return (root, *_route_location(route, root, parts))


def public_validation_error(request: Request, error: Mapping[str, Any]) -> dict[str, Any]:
    code = error.get("type")
    if not isinstance(code, str) or code not in _TYPES:
        code = "value_error"
    return {
        "loc": validated_location(request, error),
        "msg": _MESSAGES.get(code, "Invalid value."),
        "type": code,
    }
