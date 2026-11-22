from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.podcast_port import PodcastScript
from app.core.errors import AppError
from app.db.models.podcast import PodcastEpisode
from app.features.podcast.repository import EpisodeRepository
from app.features.podcast.schemas import (
    PodcastAnswers,
    PodcastCorrection,
    PodcastEpisodeOut,
    PodcastQuestionOut,
    PodcastQuizOut,
)
from app.features.podcast.service.launch import active_session, user_day
from app.features.podcast.service.runtime import PodcastRuntime
from app.features.podcast.service.store import get_episode


async def _show(db: AsyncSession, user: str, row: PodcastEpisode) -> PodcastEpisodeOut:
    script = PodcastScript.model_validate(row.script) if row.script else None
    status = row.status
    if status in {"queued", "script"} and await active_session(db, user, row.id) is None:
        status = "transcript" if script is not None else "failed"
    return PodcastEpisodeOut(
        id=row.id,
        day=row.day,
        lesson_id=row.lesson_id,
        title=row.title,
        status=status,
        lines=script.lines if script else [],
        questions=[
            PodcastQuestionOut(question=question.question, choices=question.choices)
            for question in script.questions
        ]
        if script
        else [],
        duration_seconds=row.duration_seconds,
    )


async def episode_today(
    rt: PodcastRuntime, db: AsyncSession, user: str
) -> PodcastEpisodeOut | None:
    row = await EpisodeRepository(db, user).by_day(await user_day(rt, db, user))
    return await _show(db, user, row) if row is not None else None


async def audio_bytes(rt: PodcastRuntime, db: AsyncSession, user: str, episode_id: str) -> bytes:
    row = await get_episode(db, user, episode_id)
    if row.status != "ready" or row.audio_key is None:
        raise AppError("podcast_audio_missing", "La piste audio n’est pas disponible.", 404)
    try:
        return await rt.storage.read(user, row.audio_key)
    except FileNotFoundError:
        raise AppError(
            "podcast_audio_missing", "La piste audio n’est pas disponible.", 404
        ) from None


async def correct_quiz(
    db: AsyncSession, user: str, episode_id: str, body: PodcastAnswers
) -> PodcastQuizOut:
    row = await get_episode(db, user, episode_id)
    if row.script is None:
        raise AppError("podcast_quiz_missing", "Les questions sont encore en préparation.", 409)
    script = PodcastScript.model_validate(row.script)
    corrections = [
        PodcastCorrection(
            answer=question.answer,
            correct=choice == question.answer,
            explanation=question.explanation,
        )
        for question, choice in zip(script.questions, body.choices, strict=True)
    ]
    return PodcastQuizOut(score=sum(item.correct for item in corrections), corrections=corrections)
