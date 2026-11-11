import logging
from collections.abc import Mapping
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

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
    # On ne garde que `loc`, `msg` et `type` : `input` recopierait la valeur reçue (clé d'API,
    # données personnelles) et `ctx` peut contenir des objets non sérialisables.
    errors = [{key: err[key] for key in ("loc", "msg", "type")} for err in exc.errors()]
    details = {"errors": jsonable_encoder(errors)}
    return _error_response(422, "validation_error", "Requête invalide.", details)


async def _handle_http_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    if exc.status_code == 404:
        return _error_response(404, "not_found", "Ressource introuvable.", headers=exc.headers)
    message = _HTTP_MESSAGES.get(exc.status_code, _DEFAULT_HTTP_MESSAGE)
    return _error_response(exc.status_code, "http_error", message, headers=exc.headers)


class UnexpectedErrorMiddleware:
    """Transforme toute exception non gérée en 500 au format d'erreur de l'API.

    Starlette envoie le gestionnaire `Exception` dans `ServerErrorMiddleware`, à l'extérieur de
    `CORSMiddleware` : le 500 partait sans en-tête CORS et le navigateur le masquait. Ce
    middleware est ajouté AVANT `CORSMiddleware` (donc à l'intérieur) pour que la réponse
    d'erreur traverse CORS. Les WebSockets et les réponses déjà commencées sont laissées telles
    quelles (l'exception remonte).
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = False

        async def send_wrapper(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            if started:
                raise
            logger.error("Erreur non gérée", exc_info=exc)
            response = _error_response(
                500, "internal_error", "Erreur interne. Réessaie dans un instant."
            )
            await response(scope, receive, send)


def register_error_handlers(app: FastAPI) -> None:
    """Gestionnaires d'erreurs. À appeler AVANT d'ajouter `CORSMiddleware` (voir ci-dessus)."""
    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_error)
    app.add_middleware(UnexpectedErrorMiddleware)
