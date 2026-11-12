"""Ports de la lecture du web et de YouTube, limites et erreurs.

Aucun message d'erreur ne cite l'URL, le nom d'hôte ni un extrait de la page (spec 17.2)."""

import asyncio
import re
from collections.abc import Mapping
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import parse_qs, urlsplit

from app.core.errors import AppError

FETCH_TIMEOUT_S = 15.0
FETCH_MAX_BYTES = 20 * 1024 * 1024
MAX_REDIRECTS = 5
ALLOWED_CONTENT_TYPES = (
    "text/html",
    "application/xhtml+xml",
    "text/plain",
    "text/markdown",
    "application/pdf",
)

UNREACHABLE_MESSAGE = "Page injoignable."
TIMEOUT_MESSAGE = "Délai dépassé (15 s) en lisant la page."
NO_TEXT_MESSAGE = "Page illisible : aucun texte principal trouvé."
TOO_MANY_REDIRECTS_MESSAGE = "Page injoignable : trop de redirections."
NOT_YOUTUBE_MESSAGE = "Lien YouTube non reconnu."
NO_TRANSCRIPT_MESSAGE = "Vidéo illisible : ni transcription ni description disponibles."
GITHUB_UNREADABLE = "Dépôt GitHub illisible : README absent ou API indisponible."
ARXIV_UNREADABLE = "Article arXiv introuvable ou API indisponible."

# Échéance de la lecture en cours (`loop.time()`), posée par `RoutingWebReader` : le fetch, le
# débit, le repli Gotenberg et le PDF arXiv se règlent sur ce qui reste des 15 s de la page.
READ_DEADLINE: ContextVar[float | None] = ContextVar("web_read_deadline", default=None)


def deadline_within(seconds: float) -> float:
    """Échéance à `seconds` d'ici, ramenée à celle de la lecture en cours si elle est plus
    proche. À appeler dans une boucle asyncio."""
    own = asyncio.get_running_loop().time() + seconds
    outer = READ_DEADLINE.get()
    return own if outer is None else min(own, outer)


@dataclass(frozen=True)
class FetchedResource:
    url: str
    final_url: str
    content_type: str
    body: bytes


@dataclass(frozen=True)
class WebDocument:
    url: str
    title: str | None
    text: str
    author: str | None
    date: str | None
    lang: str | None
    description: str | None


@dataclass(frozen=True)
class Transcript:
    video_id: str
    title: str | None
    text: str
    from_transcript: bool


class UrlForbidden(AppError):
    def __init__(self) -> None:
        super().__init__(
            "url_forbidden",
            "Adresse refusée : seules les adresses web publiques en http(s) sont acceptées.",
            status_code=422,
        )


class UrlTooLarge(AppError):
    def __init__(self) -> None:
        super().__init__("url_too_large", "Page trop volumineuse : 20 Mo au maximum.", 413)


class UrlUnsupported(AppError):
    def __init__(self) -> None:
        super().__init__(
            "url_unsupported_content", "Type de contenu non pris en charge à cette adresse.", 415
        )


class UrlUnreadable(AppError):
    """`message` est toujours une des constantes de ce module, jamais un texte reçu."""

    def __init__(self, message: str = UNREACHABLE_MESSAGE) -> None:
        super().__init__("url_unreadable", message, status_code=422)


class WebFetcher(Protocol):
    async def fetch(
        self,
        url: str,
        *,
        content_types: tuple[str, ...] = ALLOWED_CONTENT_TYPES,
        headers: Mapping[str, str] | None = None,
    ) -> FetchedResource:
        """`content_types` remplace la liste blanche des types (une API JSON ou Atom) ;
        `headers` s'ajoute aux en-têtes par défaut, sauf `Accept-Encoding` (D74, compatible
        D63 : un appel sans option se comporte comme avant)."""
        ...


class WebReader(Protocol):
    async def read(self, url: str, *, require_text: bool = True) -> WebDocument:
        """`require_text=False` rend la page même sans texte principal (titre et description
        seuls), pour le repli YouTube ; sinon un texte trop court lève `UrlUnreadable`."""
        ...


class YoutubeTranscripts(Protocol):
    async def transcript(self, url: str) -> Transcript: ...


_YOUTUBE_HOSTS = frozenset({"youtube.com", "www.youtube.com", "m.youtube.com"})
_VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{11}")


def youtube_video_id(url: str) -> str | None:
    """Identifiant d'une vidéo YouTube, ou `None` si l'URL n'en est pas une forme reconnue."""
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
    except ValueError:
        return None
    if parts.scheme.lower() not in ("http", "https") or parts.username or parts.password:
        return None
    segments = [s for s in parts.path.split("/") if s]
    candidate: str | None = None
    if host == "youtu.be" and len(segments) == 1:
        candidate = segments[0]
    elif host in _YOUTUBE_HOSTS:
        if segments == ["watch"]:
            values = parse_qs(parts.query).get("v", [])
            candidate = values[0] if len(values) == 1 else None
        elif len(segments) == 2 and segments[0] in ("shorts", "embed"):
            candidate = segments[1]
    return candidate if candidate and _VIDEO_ID.fullmatch(candidate) else None
