"""Size limit of the body of import requests, applied before any parsing (multipart).

Pure ASGI middleware: a declared `Content-Length` that is too large is refused without reading the
body; otherwise the bytes received are counted and, when exceeded, the read is abandoned and the
application's response (a FastAPI 400 that could not parse the body) is replaced by the 413."""

from dataclasses import dataclass

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

TOO_LARGE_CODE = "file_too_large"
TOO_LARGE_MESSAGE = "File too large: 20 MB maximum."


class BodyTooLarge(Exception):
    """Raised by the body read when exceeded; never returned as is."""


@dataclass
class _Progress:
    received: int = 0
    exceeded: bool = False
    started: bool = False


def _too_large(code: str, message: str) -> JSONResponse:
    body = {"error": {"code": code, "message": message, "details": None}}
    return JSONResponse(status_code=413, content=body)


def _declared_length(scope: Scope) -> int | None:
    for name, value in scope.get("headers", []):
        if name == b"content-length":
            try:
                return int(value)
            except ValueError:
                return None  # unreadable: the byte count applies
    return None


class BodySizeLimit:
    """POST requests on `path` or under `path/` (not `pathX`); `code` and `message`: the 413
    error returned (by default, that of a file import)."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        path: str,
        max_bytes: int,
        code: str = TOO_LARGE_CODE,
        message: str = TOO_LARGE_MESSAGE,
    ) -> None:
        self.app = app
        self.path = path
        self.max_bytes = max_bytes
        self.code = code
        self.message = message

    def _applies(self, scope: Scope) -> bool:
        path = str(scope.get("path", ""))
        return (
            scope["type"] == "http"
            and scope.get("method") == "POST"
            and (path == self.path or path.startswith(self.path + "/"))
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not self._applies(scope):
            await self.app(scope, receive, send)
            return
        declared = _declared_length(scope)
        if declared is not None and declared > self.max_bytes:
            await _too_large(self.code, self.message)(scope, receive, send)
            return
        progress = _Progress()

        async def counted_receive() -> Message:
            message = await receive()
            if message["type"] == "http.request":
                progress.received += len(message.get("body", b""))
                if progress.received > self.max_bytes:
                    progress.exceeded = True
                    raise BodyTooLarge()
            return message

        async def guarded_send(message: Message) -> None:
            if progress.exceeded:
                return  # the application's response is replaced by the 413
            if message["type"] == "http.response.start":
                progress.started = True
            await send(message)

        try:
            await self.app(scope, counted_receive, guarded_send)
        except Exception:
            if not progress.exceeded or progress.started:
                raise
        if progress.exceeded and not progress.started:
            await _too_large(self.code, self.message)(scope, receive, send)
