"""Publish the script and the quiz regardless of whether the audio is available."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.podcast_port import PodcastContext, PodcastScript
from app.core.clock import user_zone
from app.core.errors import AppError
from app.db.models.podcast import PodcastEpisode
from app.features.brain.service.reading import matching_notes
from app.features.lessons.service.lessons import ready_markdown
from app.features.podcast.repository import EpisodeRepository
from app.features.podcast.service.audio import synthesize
from app.features.podcast.service.runtime import CATEGORY, PodcastRuntime
from app.features.quiz.service.cards import due_queue
from app.features.quiz.service.podcast_review import yesterday_errors
from app.features.settings.service import SettingsService

logger = logging.getLogger(__name__)


def episode_not_found() -> AppError:
    return AppError("podcast_not_found", "Episode not found.", 404)


async def get_episode(db: AsyncSession, user_id: str, episode_id: str) -> PodcastEpisode:
    row = await EpisodeRepository(db, user_id).get(episode_id)
    if row is None:
        raise episode_not_found()
    return row


class AgentPodcastStore:
    def __init__(self, runtime: PodcastRuntime) -> None:
        self._runtime = runtime

    async def context(self, user_id: str, episode_id: str) -> PodcastContext:
        async with self._runtime.session_factory() as db:
            row = await get_episode(db, user_id, episode_id)
            if row.script is not None:
                return PodcastContext(row.title, "", (), (), True)
            markdown = await ready_markdown(db, user_id, row.module_id)
            if not markdown:
                raise AppError(
                    "podcast_source_unavailable", "This chapter is no longer published.", 409
                )
            reviews = await self._review_facts(db, user_id, row)
            notes = await matching_notes(db, user_id, (row.title,))
            excerpts = tuple(note.material for note in notes[:3])
            return PodcastContext(row.title, markdown[:14_000], reviews, excerpts, False)

    async def _review_facts(
        self, db: AsyncSession, user_id: str, row: PodcastEpisode
    ) -> tuple[str, ...]:
        settings = await SettingsService(db, user_id).get()
        missed = await yesterday_errors(db, user_id, row.day, user_zone(settings.timezone))
        queue = await due_queue(self._runtime.quiz, db, user_id)
        due = tuple(f"{card.front[:500]}\n{card.back[:500]}" for card in queue.cards[:5])
        return tuple(dict.fromkeys((*missed, *due)))[:6]

    async def save_script(self, user_id: str, episode_id: str, script: PodcastScript) -> None:
        async with self._runtime.session_factory() as db:
            row = await get_episode(db, user_id, episode_id)
            if row.script is not None:
                return
            row.script = script.model_dump(mode="json")
            row.status = "script"
            await db.commit()

    async def render_audio(self, user_id: str, episode_id: str) -> None:
        rt = self._runtime
        async with rt.locks.get(user_id, episode_id):
            async with rt.session_factory() as db:
                row = await get_episode(db, user_id, episode_id)
                if row.status != "script" or row.script is None:
                    return
                script = PodcastScript.model_validate(row.script)
            try:
                audio = await synthesize(rt.speech, user_id, script.lines)
                if not 600 <= audio.duration_seconds <= 900:
                    raise AppError(
                        "podcast_audio_duration", "The audio must last 10 to 15 minutes.", 422
                    )
                key = await rt.storage.save(user_id, CATEGORY, audio.data, ".wav")
            except (AppError, OSError) as exc:
                await self._fallback(user_id, episode_id, exc)
                return
            await self._publish(user_id, episode_id, key, audio.duration_seconds)

    async def _fallback(self, user_id: str, episode_id: str, exc: Exception) -> None:
        async with self._runtime.session_factory() as db:
            await EpisodeRepository(db, user_id).update(episode_id, status="transcript")
            await db.commit()
        code = exc.code if isinstance(exc, AppError) else type(exc).__name__
        logger.info("Podcast available without audio, episode %s, code %s", episode_id, code)

    async def _publish(self, user_id: str, episode_id: str, key: str, duration: int) -> None:
        async with self._runtime.session_factory() as db:
            row = await EpisodeRepository(db, user_id).update(
                episode_id, status="ready", audio_key=key, duration_seconds=duration
            )
            await db.commit()
        if row is None:
            await self._runtime.storage.delete(user_id, key)
