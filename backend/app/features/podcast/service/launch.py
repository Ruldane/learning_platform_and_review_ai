from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import local_today, user_zone
from app.core.errors import AppError
from app.db.models.podcast import PodcastEpisode
from app.features.podcast.repository import EpisodeRepository
from app.features.podcast.service.runtime import GRAPH, SUBJECT, PodcastRuntime
from app.features.sessions.service import find_active_session
from app.features.settings.service import SettingsService
from app.features.study.service.block import block_of_day


async def episode_for(db: AsyncSession, user_id: str, day: date) -> PodcastEpisode:
    repo = EpisodeRepository(db, user_id)
    previous = await repo.by_day(day)
    if previous is not None:
        return previous
    lesson = await block_of_day(db, user_id, day)
    if lesson is None:
        raise AppError("podcast_no_chapter", "No chapter is ready for today's block.", 409)
    return await repo.reserve(day, lesson.lesson_id, lesson.module_id, lesson.lesson_title)


async def active_session(db: AsyncSession, user_id: str, episode_id: str) -> str | None:
    return await find_active_session(
        db, user_id, graph=GRAPH, subject_type=SUBJECT, subject_id=episode_id
    )


async def user_day(rt: PodcastRuntime, db: AsyncSession, user_id: str) -> date:
    settings = await SettingsService(db, user_id).get()
    return local_today(user_zone(settings.timezone), rt.now())


async def start_episode(rt: PodcastRuntime, user_id: str, day: date | None = None) -> str:
    async with rt.locks.get(user_id, "podcast"):
        async with rt.session_factory() as db:
            episode = await episode_for(db, user_id, day or await user_day(rt, db, user_id))
            episode_id = episode.id
            session_id = await active_session(db, user_id, episode_id)
            if session_id is None and episode.status in {"ready", "transcript"}:
                session_id = episode.session_id
            await db.commit()
        if session_id is not None:
            return session_id

        async def attach(db: AsyncSession, new_id: str) -> None:
            await EpisodeRepository(db, user_id).update(episode_id, session_id=new_id)

        return await rt.launcher.start(
            user_id,
            GRAPH,
            {"episode_id": episode_id},
            subject_type=SUBJECT,
            subject_id=episode_id,
            prepare=attach,
        )
