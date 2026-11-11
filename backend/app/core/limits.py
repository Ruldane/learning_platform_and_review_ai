"""Limite de taille du corps des requêtes d'import, appliquée avant toute analyse (multipart).

Middleware ASGI pur : un `Content-Length` déclaré trop grand est refusé sans lire le corps ; sinon
les octets reçus sont comptés et, au dépassement, la lecture est abandonnée et la réponse de
l'application (une 400 de FastAPI qui n'a pas pu analyser le corps) est remplacée par la 413."""

from dataclasses import dataclass

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

TOO_LARGE_CODE = "file_too_large"
TOO_LARGE_MESSAGE = "Fichier trop volumineux : 20 Mo au maximum."


class BodyTooLarge(Exception):
    """Levée par la lecture du corps au dépassement ; jamais rendue telle quelle."""


@dataclass
class _Progress:
    received: int = 0
    exceeded: bool = False
    started: bool = False


def _too_large() -> JSONResponse:
    body = {"error": {"code": TOO_LARGE_CODE, "message": TOO_LARGE_MESSAGE, "details": None}}
    return JSONResponse(status_code=413, content=body)


def _declared_length(scope: Scope) -> int | None:
    for name, value in scope.get("headers", []):
        if name == b"content-length":
            try:
                return int(value)
            except ValueError:
                return None  # illisible : le décompte des octets s'applique
    return None


class BodySizeLimit:
    """Requêtes POST sur `path` ou sous `path/` (pas `pathX`)."""

    def __init__(self, app: ASGIApp, *, path: str, max_bytes: int) -> None:
        self.app = app
        self.path = path
        self.max_bytes = max_bytes

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
            await _too_large()(scope, receive, send)
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
                return  # la réponse de l'application est remplacée par la 413
            if message["type"] == "http.response.start":
                progress.started = True
            await send(message)

        try:
            await self.app(scope, counted_receive, guarded_send)
        except Exception:
            if not progress.exceeded or progress.started:
                raise
        if progress.exceeded and not progress.started:
            await _too_large()(scope, receive, send)
