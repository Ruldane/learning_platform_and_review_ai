"""Rendering of a web page to PDF by Gotenberg 8 (`POST /forms/chromium/convert/url`), fallback
for pages rendered in JavaScript (D72). Gotenberg only receives here a URL already validated by
the SSRF guard, never HTML; its Chromium also has its own deny list (`docker-compose.yml`).
`post_for_pdf` is also used to render our HTML templates (`html.py`, D89).

Neither the URL nor the response body appears in a message or a log."""

import asyncio
import logging

import httpx

from app.providers.pdf.base import RENDER_MAX_BYTES, RenderFailed

logger = logging.getLogger(__name__)

_ROUTE = "/forms/chromium/convert/url"
_PDF_MAGIC = b"%PDF-"

# Gotenberg multipart fields: `(file name or None, content[, type])`.
FormFiles = list[tuple[str, tuple[str | None, bytes | str] | tuple[str, bytes, str]]]


def _form(url: str) -> FormFiles:
    """Multipart fields without a file name. Wait for the idle network (no connection during
    500 ms): a single-page application has loaded its data. A page that never settles
    falls within the call's timeout. `skipNetworkAlmostIdleEvent=false` never succeeds under
    8.40.0, even on a static page (checked: 30 s then 503)."""
    return [("url", (None, url)), ("skipNetworkIdleEvent", (None, "false"))]


async def post_for_pdf(
    http: httpx.AsyncClient, endpoint: str, files: FormFiles, *, timeout_s: float
) -> bytes:
    """Sends the form and returns the PDF (rules of D72, shared with the HTML rendering of D89):
    everything under `asyncio.timeout`, status != 200, body beyond `RENDER_MAX_BYTES`, response
    without `%PDF-`, timeout or network error -> `RenderFailed` raised `from None`; log: exception
    type or status, never the form or the response."""
    try:
        async with asyncio.timeout(timeout_s):
            return await _render(http, endpoint, files)
    except (TimeoutError, httpx.HTTPError) as exc:
        # Type only: the message of an httpx error may quote the address.
        logger.info("Gotenberg rendering failed (%s)", type(exc).__name__)
        raise RenderFailed() from None


async def _render(http: httpx.AsyncClient, endpoint: str, files: FormFiles) -> bytes:
    async with http.stream("POST", endpoint, files=files) as response:
        if response.status_code != 200:
            logger.info("Gotenberg rendering refused (status %s)", response.status_code)
            raise RenderFailed() from None
        body = bytearray()
        async for chunk in response.aiter_bytes():
            body += chunk
            if len(body) > RENDER_MAX_BYTES:
                logger.info("Gotenberg rendering too large")
                raise RenderFailed() from None
    if not body.startswith(_PDF_MAGIC):
        logger.info("Gotenberg rendering: response is not a PDF")
        raise RenderFailed() from None
    return bytes(body)


class GotenbergRenderer:
    """`PageRenderer` on a dedicated client (`bootstrap._render_http`)."""

    def __init__(self, http: httpx.AsyncClient, base_url: str) -> None:
        self._http = http
        self._endpoint = base_url.rstrip("/") + _ROUTE

    async def url_to_pdf(self, url: str, *, timeout_s: float) -> bytes:
        return await post_for_pdf(self._http, self._endpoint, _form(url), timeout_s=timeout_s)
