"""Erreurs de saisie des routes du CV : une 422 nomme les champs par leur chemin
(`details.fields`, « experiences.2.role »), sans valeur ni message de pydantic qui pourrait la
citer (SPEC 17.2 : le profil et le CV sont des données personnelles)."""

from collections.abc import Callable, Coroutine, Sequence
from typing import Any

from fastapi import Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute

from app.core.errors import AppError

_ROOTS = ("body", "query", "path", "header", "cookie")
_WRAPPERS = ("data",)  # `ProfilePutIn.data` : le chemin part du profil lui-même


def field_paths(errors: Sequence[Any]) -> list[str]:
    """Chemins sans la racine (`body`) ni l'enveloppe `data`, dans l'ordre, sans doublon."""
    paths: list[str] = []
    for error in errors:
        loc = [str(part) for part in error.get("loc", ())]
        if loc and loc[0] in _ROOTS and len(loc) > 1:
            loc = loc[1:]
        if len(loc) > 1 and loc[0] in _WRAPPERS:
            loc = loc[1:]
        path = ".".join(loc) or "body"
        if path not in paths:
            paths.append(path)
    return paths


def invalid_fields(errors: Sequence[Any]) -> AppError:
    return AppError(
        "validation_error",
        "Requête invalide : vérifie les champs signalés.",
        422,
        {"fields": field_paths(errors)},
    )


class FieldPathsRoute(APIRoute):
    """Route dont la 422 de validation porte `details.fields` au lieu de `details.errors`."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        handler = super().get_route_handler()

        async def route(request: Request) -> Response:
            try:
                return await handler(request)
            except RequestValidationError as exc:
                raise invalid_fields(exc.errors()) from None

        return route
