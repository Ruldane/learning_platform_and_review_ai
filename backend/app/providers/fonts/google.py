"""Free fonts from Google Fonts (D119): the CSS2 stylesheet (`fonts.googleapis.com`) gives
the address of each file (`fonts.gstatic.com`); these two hosts only, over HTTPS, 15 s per
request, 2 MB per file, no redirect followed.

A neutral user agent gets complete TrueType files served (one file per weight,
all characters), where a browser receives `woff2` split by alphabet. "Liberation
Sans" and "Liberation Serif" are not there: Google serves their twins "Arimo" and "Tinos"
(same design, same metrics), returned under the catalogue's name.

Log: status and number of files, never the family (it would betray the PDF's font, D126),
the address or the response."""

import asyncio
import logging
import re
from collections.abc import Sequence
from typing import Literal
from urllib.parse import urlsplit

import httpx

from app.providers.fonts.base import (
    DEFAULT_WEIGHTS,
    FONT_MAX_BYTES,
    FONT_TIMEOUT_S,
    FontFile,
    FontUnavailable,
)
from app.providers.fonts.catalog import FREE_FAMILIES

logger = logging.getLogger(__name__)

CSS_URL = "https://fonts.googleapis.com/css2"
FILES_HOST = "fonts.gstatic.com"
USER_AGENT = "Tremplin"
_CSS_MAX_BYTES = 64 * 1024
_GOOGLE_NAMES = {"Liberation Sans": "Arimo", "Liberation Serif": "Tinos"}
_FACE = re.compile(r"@font-face\s*\{([^}]*)\}")
_STYLE = re.compile(r"font-style:\s*(normal|italic)")
_WEIGHT = re.compile(r"font-weight:\s*(\d{3})\s*;")
_SRC = re.compile(r"src:\s*url\(([^)\s'\"]+)\)\s*format\('(truetype|woff2)'\)")
_SUFFIXES: dict[str, Literal[".woff2", ".ttf"]] = {"truetype": ".ttf", "woff2": ".woff2"}
# Signatures: TrueType (version 1.0 or "true"), OpenType CFF, WOFF2.
_MAGIC = {".ttf": (b"\x00\x01\x00\x00", b"true", b"OTTO"), ".woff2": (b"wOF2",)}


def fonts_http() -> httpx.AsyncClient:
    """Google Fonts client, opened by the composition: no proxy or environment
    setting, no redirect, 15 s."""
    return httpx.AsyncClient(follow_redirects=False, trust_env=False, timeout=FONT_TIMEOUT_S)


def _faces(css: str, weights: set[int]) -> dict[int, tuple[str, str]]:
    """Weight -> (address, format) of the requested normal faces; the first face of a weight
    wins (without `unicode-range` with our user agent)."""
    found: dict[int, tuple[str, str]] = {}
    for body in _FACE.findall(css):
        style, weight, src = _STYLE.search(body), _WEIGHT.search(body), _SRC.search(body)
        if style is None or weight is None or src is None or style.group(1) != "normal":
            continue
        value = int(weight.group(1))
        if value in weights and value not in found:
            found[value] = (src.group(1), src.group(2))
    return found


async def _get(http: httpx.AsyncClient, url: str, limit: int, **params: str) -> bytes:
    """Body of a 200 response from `url`, `limit` bytes at most; `FontUnavailable` otherwise."""
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in {"fonts.googleapis.com", FILES_HOST}:
        raise _Refused("host refused")
    async with (
        asyncio.timeout(FONT_TIMEOUT_S),
        http.stream("GET", url, params=params, headers={"User-Agent": USER_AGENT}) as response,
    ):
        if response.status_code != 200:
            raise _Refused(f"status {response.status_code}")
        body = bytearray()
        async for chunk in response.aiter_bytes():
            body += chunk
            if len(body) > limit:
                raise _Refused("too large")
    return bytes(body)


class _Refused(Exception):
    """Refusal readable in the log: never the address or the body."""

    def __init__(self, reason: str) -> None:
        self.reason = reason


class GoogleFontsSource:
    """`FontSource` of the composition, on the `fonts_http` client."""

    def __init__(self, http: httpx.AsyncClient) -> None:
        self._http = http

    async def fetch(self, family: str, weights: Sequence[int] = DEFAULT_WEIGHTS) -> list[FontFile]:
        wanted = sorted({w for w in weights if w in range(100, 1000, 100)})
        if family not in FREE_FAMILIES or not wanted:
            raise FontUnavailable()
        try:
            return await self._fetch(family, wanted)
        except _Refused as refused:
            logger.info("Font unavailable (%s)", refused.reason)
        except (TimeoutError, httpx.HTTPError, UnicodeDecodeError) as exc:
            # Type only: the message of an httpx error may quote the address.
            logger.info("Font unavailable (%s)", type(exc).__name__)
        raise FontUnavailable() from None

    async def _fetch(self, family: str, weights: list[int]) -> list[FontFile]:
        name = _GOOGLE_NAMES.get(family, family)
        spec = f"{name}:wght@{';'.join(str(w) for w in weights)}"
        css = (await _get(self._http, CSS_URL, _CSS_MAX_BYTES, family=spec)).decode("utf-8")
        faces = _faces(css, set(weights))
        if set(faces) != set(weights):
            # Never a partial result: the template relies on each weight (review 6.3, M5).
            raise _Refused("weight missing")
        files: list[FontFile] = []
        for weight, (url, kind) in sorted(faces.items()):
            suffix = _SUFFIXES[kind]
            data = await _get(self._http, url, FONT_MAX_BYTES)
            if not data.startswith(_MAGIC[suffix]):
                raise _Refused("invalid file")
            files.append(FontFile(family, weight, "normal", data, suffix))
        logger.info("Font loaded (%s files)", len(files))
        return files
