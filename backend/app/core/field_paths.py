"""Input errors of the routes with named fields (CV, applications): a 422 names the fields by
their path (`details.fields`, « experiences.2.role »), without any value or pydantic message
that could quote it (SPEC 17.2: profile, CV and applications are personal data)."""

from collections.abc import Callable, Coroutine, Sequence
from typing import Any

from fastapi import Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute

from app.core.errors import AppError
from app.core.validation import ROOTS, validated_location

_WRAPPERS = ("data",)  # `ProfilePutIn.data`: the path starts from the profile itself


def field_paths(request: Request, errors: Sequence[Any]) -> list[str]:
    """Paths without the root (`body`) or the `data` envelope, in order, without duplicates."""
    paths: list[str] = []
    for error in errors:
        loc = [str(part) for part in validated_location(request, error)]
        if loc and loc[0] in ROOTS and len(loc) > 1:
            loc = loc[1:]
        if len(loc) > 1 and loc[0] in _WRAPPERS:
            loc = loc[1:]
        path = ".".join(loc) or "body"
        if path not in paths:
            paths.append(path)
    return paths


def invalid_fields(request: Request, errors: Sequence[Any]) -> AppError:
    return AppError(
        "validation_error",
        "Invalid request. Check the highlighted fields.",
        422,
        {"fields": field_paths(request, errors)},
    )


class FieldPathsRoute(APIRoute):
    """Route whose validation 422 carries `details.fields` instead of `details.errors`."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        handler = super().get_route_handler()

        async def route(request: Request) -> Response:
            try:
                return await handler(request)
            except RequestValidationError as exc:
                raise invalid_fields(request, exc.errors()) from None

        return route
