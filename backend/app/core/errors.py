import logging
from collections.abc import Mapping
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.validation import public_validation_error

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Business error rendered as `{"error": {"code", "message", "details"}}`."""

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
    401: "Sign-in required.",
    403: "Access denied.",
    405: "Method not allowed.",
    429: "Too many requests, try again in a moment.",
}
_DEFAULT_HTTP_MESSAGE = "The request could not be completed."


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


async def _handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    details = {"errors": [public_validation_error(request, error) for error in exc.errors()]}
    return _error_response(422, "validation_error", "Invalid request.", details)


async def _handle_http_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    if exc.status_code == 404:
        return _error_response(404, "not_found", "Resource not found.", headers=exc.headers)
    message = _HTTP_MESSAGES.get(exc.status_code, _DEFAULT_HTTP_MESSAGE)
    return _error_response(exc.status_code, "http_error", message, headers=exc.headers)


class UnexpectedErrorMiddleware:
    """Turns any unhandled exception into a 500 in the API error format.

    Starlette sends the `Exception` handler to `ServerErrorMiddleware`, outside
    `CORSMiddleware`: the 500 left without a CORS header and the browser hid it. This
    middleware is added BEFORE `CORSMiddleware` (so inside it) so that the error response
    goes through CORS. WebSockets and responses already started are left as they are (the
    exception propagates).
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
            logger.error("Unhandled error", exc_info=exc)
            response = _error_response(
                500, "internal_error", "Internal error. Try again in a moment."
            )
            await response(scope, receive, send)


def register_error_handlers(app: FastAPI) -> None:
    """Error handlers. Call BEFORE adding `CORSMiddleware` (see above)."""
    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_error)
    app.add_middleware(UnexpectedErrorMiddleware)
