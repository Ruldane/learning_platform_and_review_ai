"""Rendu d'une page web en PDF par Gotenberg 8 (`POST /forms/chromium/convert/url`), repli des
pages rendues en JavaScript (D72). Gotenberg ne reçoit ici qu'une URL déjà validée par la garde
SSRF, jamais de HTML ; son Chromium a en plus sa propre liste de refus (`docker-compose.yml`).
`post_for_pdf` sert aussi au rendu de nos gabarits HTML (`html.py`, D89).

Ni l'URL ni le corps de la réponse n'apparaissent dans un message ou un journal."""

import asyncio
import logging

import httpx

from app.providers.pdf.base import RENDER_MAX_BYTES, RenderFailed

logger = logging.getLogger(__name__)

_ROUTE = "/forms/chromium/convert/url"
_PDF_MAGIC = b"%PDF-"

# Champs multipart de Gotenberg : `(nom de fichier ou None, contenu[, type])`.
FormFiles = list[tuple[str, tuple[str | None, bytes | str] | tuple[str, bytes, str]]]


def _form(url: str) -> FormFiles:
    """Champs multipart sans nom de fichier. Attente du réseau inactif (aucune connexion pendant
    500 ms) : une application monopage a chargé ses données. Une page qui ne s'arrête jamais
    tombe dans le délai de l'appel. `skipNetworkAlmostIdleEvent=false` n'aboutit jamais sous
    8.40.0, même sur une page statique (vérifié : 30 s puis 503)."""
    return [("url", (None, url)), ("skipNetworkIdleEvent", (None, "false"))]


async def post_for_pdf(
    http: httpx.AsyncClient, endpoint: str, files: FormFiles, *, timeout_s: float
) -> bytes:
    """Envoie le formulaire et rend le PDF (règles de D72, partagées avec le rendu HTML de D89) :
    tout sous `asyncio.timeout`, statut ≠ 200, corps au-delà de `RENDER_MAX_BYTES`, réponse sans
    `%PDF-`, délai ou erreur réseau → `RenderFailed` levée `from None` ; journal : type
    d'exception ou statut, jamais le formulaire ni la réponse."""
    try:
        async with asyncio.timeout(timeout_s):
            return await _render(http, endpoint, files)
    except (TimeoutError, httpx.HTTPError) as exc:
        # Type seul : le message d'une erreur httpx peut citer l'adresse.
        logger.info("Rendu Gotenberg impossible (%s)", type(exc).__name__)
        raise RenderFailed() from None


async def _render(http: httpx.AsyncClient, endpoint: str, files: FormFiles) -> bytes:
    async with http.stream("POST", endpoint, files=files) as response:
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


class GotenbergRenderer:
    """`PageRenderer` sur un client dédié (`bootstrap._render_http`)."""

    def __init__(self, http: httpx.AsyncClient, base_url: str) -> None:
        self._http = http
        self._endpoint = base_url.rstrip("/") + _ROUTE

    async def url_to_pdf(self, url: str, *, timeout_s: float) -> bytes:
        return await post_for_pdf(self._http, self._endpoint, _form(url), timeout_s=timeout_s)
