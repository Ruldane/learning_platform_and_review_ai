"""Polices libres depuis Google Fonts (D119) : la feuille CSS2 (`fonts.googleapis.com`) donne
l'adresse de chaque fichier (`fonts.gstatic.com`) ; ces deux hôtes seulement, en HTTPS, 15 s par
requête, 2 Mo par fichier, aucune redirection suivie.

Un agent utilisateur neutre fait servir des fichiers TrueType complets (un fichier par graisse,
tous les caractères), là où un navigateur reçoit du `woff2` découpé par alphabet. « Liberation
Sans » et « Liberation Serif » n'y sont pas : Google sert leurs jumelles « Arimo » et « Tinos »
(même dessin, mêmes métriques), rendues sous le nom du catalogue.

Journal : statut et nombre de fichiers, jamais la famille (elle trahirait la police du PDF, D126),
l'adresse ni la réponse."""

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
# Signatures : TrueType (version 1.0 ou « true »), OpenType CFF, WOFF2.
_MAGIC = {".ttf": (b"\x00\x01\x00\x00", b"true", b"OTTO"), ".woff2": (b"wOF2",)}


def fonts_http() -> httpx.AsyncClient:
    """Client de Google Fonts, ouvert par la composition : ni proxy ni réglage de
    l'environnement, aucune redirection, 15 s."""
    return httpx.AsyncClient(follow_redirects=False, trust_env=False, timeout=FONT_TIMEOUT_S)


def _faces(css: str, weights: set[int]) -> dict[int, tuple[str, str]]:
    """Graisse → (adresse, format) des faces normales demandées ; la première face d'une graisse
    l'emporte (sans `unicode-range` avec notre agent utilisateur)."""
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
    """Corps d'une réponse 200 de `url`, `limit` octets au plus ; `FontUnavailable` sinon."""
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in {"fonts.googleapis.com", FILES_HOST}:
        raise _Refused("hôte refusé")
    async with (
        asyncio.timeout(FONT_TIMEOUT_S),
        http.stream("GET", url, params=params, headers={"User-Agent": USER_AGENT}) as response,
    ):
        if response.status_code != 200:
            raise _Refused(f"statut {response.status_code}")
        body = bytearray()
        async for chunk in response.aiter_bytes():
            body += chunk
            if len(body) > limit:
                raise _Refused("trop volumineux")
    return bytes(body)


class _Refused(Exception):
    """Refus lisible dans le journal : jamais l'adresse ni le corps."""

    def __init__(self, reason: str) -> None:
        self.reason = reason


class GoogleFontsSource:
    """`FontSource` de la composition, sur le client de `fonts_http`."""

    def __init__(self, http: httpx.AsyncClient) -> None:
        self._http = http

    async def fetch(self, family: str, weights: Sequence[int] = DEFAULT_WEIGHTS) -> list[FontFile]:
        wanted = sorted({w for w in weights if w in range(100, 1000, 100)})
        if family not in FREE_FAMILIES or not wanted:
            raise FontUnavailable()
        try:
            return await self._fetch(family, wanted)
        except _Refused as refused:
            logger.info("Police indisponible (%s)", refused.reason)
        except (TimeoutError, httpx.HTTPError, UnicodeDecodeError) as exc:
            # Type seul : le message d'une erreur httpx peut citer l'adresse.
            logger.info("Police indisponible (%s)", type(exc).__name__)
        raise FontUnavailable() from None

    async def _fetch(self, family: str, weights: list[int]) -> list[FontFile]:
        name = _GOOGLE_NAMES.get(family, family)
        spec = f"{name}:wght@{';'.join(str(w) for w in weights)}"
        css = (await _get(self._http, CSS_URL, _CSS_MAX_BYTES, family=spec)).decode("utf-8")
        faces = _faces(css, set(weights))
        if set(faces) != set(weights):
            # Résultat jamais partiel : le gabarit compte sur chaque graisse (revue 6.3, M5).
            raise _Refused("graisse absente")
        files: list[FontFile] = []
        for weight, (url, kind) in sorted(faces.items()):
            suffix = _SUFFIXES[kind]
            data = await _get(self._http, url, FONT_MAX_BYTES)
            if not data.startswith(_MAGIC[suffix]):
                raise _Refused("fichier invalide")
            files.append(FontFile(family, weight, "normal", data, suffix))
        logger.info("Police chargée (%s fichiers)", len(files))
        return files
