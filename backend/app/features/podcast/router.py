from typing import Annotated

from fastapi import APIRouter, Depends, Response
from starlette.requests import HTTPConnection

from app.core.deps import CurrentUserDep, Db
from app.features.podcast.schemas import (
    PodcastAnswers,
    PodcastEpisodeOut,
    PodcastQuizOut,
    PodcastStarted,
)
from app.features.podcast.service.launch import start_episode
from app.features.podcast.service.runtime import PodcastRuntime
from app.features.podcast.service.views import audio_bytes, correct_quiz, episode_today

router = APIRouter(prefix="/podcast", tags=["podcast"])


def runtime(conn: HTTPConnection) -> PodcastRuntime:
    found: PodcastRuntime = conn.app.state.daily.podcast
    return found


PodcastDep = Annotated[PodcastRuntime, Depends(runtime)]


@router.get("/today", response_model=PodcastEpisodeOut | None)
async def get_today(current: CurrentUserDep, db: Db, rt: PodcastDep) -> PodcastEpisodeOut | None:
    return await episode_today(rt, db, current.id)


@router.post("/today", response_model=PodcastStarted, status_code=202)
async def create_today(current: CurrentUserDep, rt: PodcastDep) -> PodcastStarted:
    return PodcastStarted(session_id=await start_episode(rt, current.id))


@router.get("/{episode_id}/audio", responses={200: {"content": {"audio/wav": {}}}})
async def get_audio(episode_id: str, current: CurrentUserDep, db: Db, rt: PodcastDep) -> Response:
    return Response(
        await audio_bytes(rt, db, current.id, episode_id),
        media_type="audio/wav",
        headers={"Cache-Control": "private, max-age=3600"},
    )


@router.post("/{episode_id}/quiz", response_model=PodcastQuizOut)
async def post_quiz(
    episode_id: str, body: PodcastAnswers, current: CurrentUserDep, db: Db
) -> PodcastQuizOut:
    return await correct_quiz(db, current.id, episode_id, body)
