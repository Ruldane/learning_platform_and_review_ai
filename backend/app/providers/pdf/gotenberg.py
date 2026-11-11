"""Rendu d'une page web en PDF par Gotenberg 8 (`POST /forms/chromium/convert/url`), repli des
pages rendues en JavaScript (D72). Gotenberg ne reçoit qu'une URL déjà validée par la garde SSRF,
jamais de HTML ; son Chromium a en plus sa propre liste de refus (`docker-compose.yml`).

Ni l'URL ni le corps de la réponse n'apparaissent dans un message ou un journal."""

import asyncio
import logging

import httpx

from app.providers.pdf.base import RENDER_MAX_BYTES, RenderFailed

logger = logging.getLogger(__name__)

_ROUTE = "/forms/chromium/convert/url"
_PDF_MAGIC = b"%PDF-"


def _form(url: str) -> dict[str, tuple[None, str]]:
    """Champs multipart sans nom de fichier. Attente du réseau inactif (aucune connexion pendant
    500 ms) : une application monopage a chargé ses données. Une page qui ne s'arrête jamais
    tombe dans le délai de l'appel. `skipNetworkAlmostIdleEvent=false` n'aboutit jamais sous
    8.40.0, même sur une page statique (vérifié : 30 s puis 503)."""
    return {"url": (None, url), "skipNetworkIdleEvent": (None, "false")}


class GotenbergRenderer:
    """`PageRenderer` sur un client dédié (`bootstrap._render_http`)."""

    def __init__(self, http: httpx.AsyncClient, base_url: str) -> None:
        self._http = http
        self._endpoint = base_url.rstrip("/") + _ROUTE

    async def url_to_pdf(self, url: str, *, timeout_s: float) -> bytes:
        try:
            async with asyncio.timeout(timeout_s):
                return await self._render(url)
        except (TimeoutError, httpx.HTTPError) as exc:
            # Type seul : le message d'une erreur httpx peut citer l'adresse.
            logger.info("Rendu Gotenberg impossible (%s)", type(exc).__name__)
            raise RenderFailed() from None

    async def _render(self, url: str) -> bytes:
        async with self._http.stream("POST", self._endpoint, files=_form(url)) as response:
            if response.status_code != 200:
                logger.info("Rendu Gotenberg refusé (statut %s)", response.status_code)
                raise RenderFailed() from None
            body = bytearray()
            async for chunk in response.aiter_bytes():
                body += chunk
                if len(body) > RENDER_MAX_BYTES:
                    logger.info("Rendu Gotenberg trop volumineux")
                    raise RenderFailed() from None
        if not body.startswith(_PDF_MAGIC):
            logger.info("Rendu Gotenberg : réponse qui n'est pas un PDF")
            raise RenderFailed() from None
        return bytes(body)
