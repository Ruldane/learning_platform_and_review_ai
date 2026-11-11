import logging
from collections.abc import Mapping
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Erreur métier rendue au format `{"error": {"code", "message", "details"}}`."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


_HTTP_MESSAGES = {
    401: "Connexion requise.",
    403: "Accès refusé.",
    405: "Méthode non autorisée.",
    429: "Trop de requêtes, réessaie dans un instant.",
}
_DEFAULT_HTTP_MESSAGE = "La requête n'a pas pu aboutir."


def _error_response(
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    body = {"error": {"code": code, "message": message, "details": details}}
    return JSONResponse(status_code=status_code, content=body, headers=headers)


async def _handle_app_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    return _error_response(exc.status_code, exc.code, exc.message, exc.details)


async def _handle_validation_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    # exc.errors() peut contenir des objets non sérialisables (ex. ValueError) : on les encode.
    details = {"errors": jsonable_encoder(exc.errors())}
    return _error_response(422, "validation_error", "Requête invalide.", details)


async def _handle_http_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    if exc.status_code == 404:
        return _error_response(404, "not_found", "Ressource introuvable.", headers=exc.headers)
    message = _HTTP_MESSAGES.get(exc.status_code, _DEFAULT_HTTP_MESSAGE)
    return _error_response(exc.status_code, "http_error", message, headers=exc.headers)


async def _handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
    logger.error("Erreur non gérée", exc_info=exc)
    return _error_response(500, "internal_error", "Erreur interne. Réessaie dans un instant.")


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_error)
    app.add_exception_handler(Exception, _handle_unexpected_error)
