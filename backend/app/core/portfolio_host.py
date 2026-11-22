"""L’hôte public sert uniquement les fichiers explicitement approuvés."""

from collections.abc import Callable

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.portfolio_urls import PUBLIC_PATH, matches_public_host


class PortfolioPublicHostGuard:
    def __init__(self, app: ASGIApp, origin: Callable[[], str | None]) -> None:
        self._app = app
        self._origin = origin

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        origin = self._origin()
        if not origin or scope["type"] not in {"http", "websocket"}:
            await self._app(scope, receive, send)
            return
        host = Headers(scope=scope).get("host", "")
        if not matches_public_host(origin, host):
            await self._app(scope, receive, send)
            return
        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1008})
        elif scope["method"] == "GET" and scope["path"].startswith(PUBLIC_PATH):
            await self._app(scope, receive, send)
        else:
            reply = JSONResponse(
                {
                    "error": {
                        "code": "not_found",
                        "message": "Ressource introuvable.",
                        "details": None,
                    }
                },
                status_code=404,
                headers={"Cache-Control": "no-store"},
            )
            await reply(scope, receive, send)
