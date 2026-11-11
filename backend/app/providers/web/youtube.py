"""Transcriptions YouTube avec `youtube-transcript-api` (1.x), repli sur le titre et la
description de la page.

La bibliothèque n'appelle que YouTube (hôte fixe) avec un identifiant validé par
`youtube_video_id` : aucune URL reçue ne lui est transmise. La page de repli passe par notre
lecteur sûr. Les journaux ne citent que le type d'erreur."""

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
REQUEST_TIMEOUT_S = (5.0, 10.0)  # connexion, lecture : `asyncio.timeout` n'arrête pas le thread


class BoundedSession(Session):
    """Session de la bibliothèque : délai par défaut sur chaque requête (sans lui, un thread
    resterait bloqué au-delà des 15 s) et aucun proxy ni `.netrc` de l'environnement."""

    def __init__(self) -> None:
        super().__init__()
        self.trust_env = False

    def request(self, *args: Any, **kwargs: Any) -> Response:
        kwargs.setdefault("timeout", REQUEST_TIMEOUT_S)
        return super().request(*args, **kwargs)


def _fetch_text(video_id: str, languages: tuple[str, ...]) -> str:
    """Bloquant (requests) : appelé dans un thread."""
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
            # Toute erreur (désactivée, absente, bloquée, réseau, délai) mène au repli.
            logger.info("Transcription YouTube indisponible (%s)", type(exc).__name__)
            return ""

    async def _page(self, video_id: str) -> WebDocument | None:
        """Page `watch?v=<id>` lue par le lecteur sûr, sans exiger de texte principal."""
        try:
            return await self._reader.read(
                f"https://www.youtube.com/watch?v={video_id}", require_text=False
            )
        except AppError as exc:
            logger.info("Page YouTube illisible (%s)", exc.code)
            return None
