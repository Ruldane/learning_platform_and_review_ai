"""Ports for reading the web and YouTube, limits and errors.

No error message quotes the URL, the host name or an extract of the page (spec 17.2)."""

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

UNREACHABLE_MESSAGE = "Page unreachable."
TIMEOUT_MESSAGE = "Timed out (15 s) while reading the page."
NO_TEXT_MESSAGE = "Page unreadable: no main text found."
TOO_MANY_REDIRECTS_MESSAGE = "Page unreachable: too many redirects."
NOT_YOUTUBE_MESSAGE = "YouTube link not recognised."
NO_TRANSCRIPT_MESSAGE = "Video unreadable: neither transcript nor description available."
GITHUB_UNREADABLE = "GitHub repository unreadable: README missing or API unavailable."
ARXIV_UNREADABLE = "arXiv paper not found or API unavailable."

# Deadline of the read in progress (`loop.time()`), set by `RoutingWebReader`: the fetch, the
# rate limit, the Gotenberg fallback and the arXiv PDF all follow what remains of the page's 15 s.
READ_DEADLINE: ContextVar[float | None] = ContextVar("web_read_deadline", default=None)


def deadline_within(seconds: float) -> float:
    """Deadline `seconds` from now, brought down to that of the read in progress if it is
    closer. To be called inside an asyncio loop."""
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
            "Use a public HTTP or HTTPS link.",
            status_code=422,
        )


class UrlTooLarge(AppError):
    def __init__(self) -> None:
        super().__init__("url_too_large", "Page too large: 20 MB maximum.", 413)


class UrlUnsupported(AppError):
    def __init__(self) -> None:
        super().__init__(
            "url_unsupported_content", "Content type not supported at this address.", 415
        )


class UrlUnreadable(AppError):
    """`message` is always one of the constants of this module, never a received text."""

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
        """`content_types` replaces the whitelist of types (a JSON or Atom API);
        `headers` is added to the default headers, except `Accept-Encoding` (D74, compatible
        with D63: a call without options behaves as before)."""
        ...


class WebReader(Protocol):
    async def read(self, url: str, *, require_text: bool = True) -> WebDocument:
        """`require_text=False` returns the page even without main text (title and description
        only), for the YouTube fallback; otherwise a text that is too short raises
        `UrlUnreadable`."""
        ...


class YoutubeTranscripts(Protocol):
    async def transcript(self, url: str) -> Transcript: ...


_YOUTUBE_HOSTS = frozenset({"youtube.com", "www.youtube.com", "m.youtube.com"})
_VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{11}")


def youtube_video_id(url: str) -> str | None:
    """Identifier of a YouTube video, or `None` if the URL is not a recognised form of one."""
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
