"""YouTube transcripts with `youtube-transcript-api` (1.x), falling back on the page's title and
description.

The library only calls YouTube (fixed host) with an identifier validated by
`youtube_video_id`: no received URL is passed to it. The fallback page goes through our safe
reader. The logs only quote the error type."""

import asyncio
import logging
from typing import Any

from requests import Response, Session
from youtube_transcript_api import YouTubeTranscriptApi

from app.core.errors import AppError
from app.providers.web.base import (
    NO_TRANSCRIPT_MESSAGE,
    NOT_YOUTUBE_MESSAGE,
    Transcript,
    UrlUnreadable,
    WebDocument,
    WebReader,
    youtube_video_id,
)

logger = logging.getLogger(__name__)

TRANSCRIPT_TIMEOUT_S = 15.0
REQUEST_TIMEOUT_S = (5.0, 10.0)  # connect, read: `asyncio.timeout` does not stop the thread


class BoundedSession(Session):
    """The library's session: default timeout on each request (without it, a thread
    would stay blocked beyond the 15 s) and no proxy or `.netrc` from the environment."""

    def __init__(self) -> None:
        super().__init__()
        self.trust_env = False

    def request(self, *args: Any, **kwargs: Any) -> Response:
        kwargs.setdefault("timeout", REQUEST_TIMEOUT_S)
        return super().request(*args, **kwargs)


def _fetch_text(video_id: str, languages: tuple[str, ...]) -> str:
    """Blocking (requests): called in a thread."""
    with BoundedSession() as session:
        fetched = YouTubeTranscriptApi(http_client=session).fetch(video_id, languages=languages)
    return " ".join(" ".join(snippet.text for snippet in fetched).split())


class TranscriptApiYoutube:
    def __init__(self, reader: WebReader, *, languages: tuple[str, ...] = ("fr", "en")) -> None:
        self._reader = reader
        self._languages = languages

    async def transcript(self, url: str) -> Transcript:
        video_id = youtube_video_id(url)
        if video_id is None:
            raise UrlUnreadable(NOT_YOUTUBE_MESSAGE)
        text = await self._transcript_text(video_id)
        page = await self._page(video_id)
        if text:
            return Transcript(video_id, page.title if page else None, text, True)
        description = (page.description or "").strip() if page else ""
        if page is None or not description:
            raise UrlUnreadable(NO_TRANSCRIPT_MESSAGE)
        title = (page.title or "").strip()
        body = f"{title}\n\n{description}" if title else description
        return Transcript(video_id, title or None, body, False)

    async def _transcript_text(self, video_id: str) -> str:
        try:
            async with asyncio.timeout(TRANSCRIPT_TIMEOUT_S):
                return await asyncio.to_thread(_fetch_text, video_id, self._languages)
        except Exception as exc:
            # Any error (disabled, missing, blocked, network, timeout) leads to the fallback.
            logger.info("YouTube transcript unavailable (%s)", type(exc).__name__)
            return ""

    async def _page(self, video_id: str) -> WebDocument | None:
        """Page `watch?v=<id>` read by the safe reader, without requiring main text."""
        try:
            return await self._reader.read(
                f"https://www.youtube.com/watch?v={video_id}", require_text=False
            )
        except AppError as exc:
            logger.info("YouTube page unreadable (%s)", exc.code)
            return None
