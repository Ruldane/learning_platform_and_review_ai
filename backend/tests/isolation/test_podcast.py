import wave
from dataclasses import dataclass
from io import BytesIO

import httpx
import pytest
from fastapi import FastAPI
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.podcast_port import PodcastLine, PodcastQuestion, PodcastScript
from app.db.base import new_id
from app.features.podcast.repository import EpisodeRepository
from app.features.podcast.service.launch import user_day
from app.features.podcast.service.runtime import PodcastRuntime
from app.features.podcast.service.store import AgentPodcastStore
from app.providers.speech.base import PCM_RATE, Speaker, SpeechUnavailable
from tests.isolation.conftest import Browser

API = "/api/v1/podcast"
SCRIPT = PodcastScript(
    lines=[
        PodcastLine(speaker="host", text="Que fait une chaîne ?"),
        PodcastLine(speaker="coach", text="Elle relie des étapes."),
    ],
    questions=[
        PodcastQuestion(
            question=f"Question {index}",
            choices=["Un", "Deux", "Trois"],
            answer=1,
            explanation="Deux étapes sont reliées.",
        )
        for index in range(3)
    ],
)


@dataclass
class Voices:
    fail_for: str
    called: list[Speaker]
    seconds: int = 302

    async def speak(self, user_id: str, speaker: Speaker, text: str) -> bytes:
        if user_id == self.fail_for:
            raise SpeechUnavailable()
        self.called.append(speaker)
        return b"\0\0" * (PCM_RATE * self.seconds)


async def _seed(runtime: PodcastRuntime, db: AsyncSession, uid: str) -> str:
    day = await user_day(runtime, db, uid)
    episode = await EpisodeRepository(db, uid).reserve(day, new_id(), new_id(), "Chaînes")
    await db.commit()
    store = AgentPodcastStore(runtime)
    await store.save_script(uid, episode.id, SCRIPT)
    await store.render_audio(uid, episode.id)
    return episode.id


async def _user(browser: httpx.AsyncClient) -> str:
    response = await browser.get("/api/v1/auth/me")
    return str(response.json()["id"])


async def test_two_voices_and_audio_failure_keep_tenant_bound_transcripts(
    google_client_factory: Browser, google_app: FastAPI, db_session: AsyncSession
) -> None:
    owner = await google_client_factory("january@example.com")
    other = await google_client_factory("autre@example.com")
    mine, foreign = await _user(owner), await _user(other)
    runtime: PodcastRuntime = google_app.state.daily.podcast
    voices = Voices(foreign, [])
    runtime.speech = voices
    episode = await _seed(runtime, db_session, mine)
    fallback = await _seed(runtime, db_session, foreign)
    assert voices.called == ["host", "coach"]
    first = (await owner.get(f"{API}/today")).json()
    second = (await other.get(f"{API}/today")).json()
    assert (first["id"], first["status"]) == (episode, "ready")
    assert (second["id"], second["status"]) == (fallback, "transcript")
    assert len(second["lines"]) == 2 and len(second["questions"]) == 3
    assert "answer" not in second["questions"][0]
    score = await other.post(f"{API}/{fallback}/quiz", json={"choices": [1, 0, 1]})
    assert score.json()["score"] == 2
    audio = await owner.get(f"{API}/{episode}/audio")
    assert audio.headers["content-type"] == "audio/wav"
    with wave.open(BytesIO(audio.content), "rb") as wav:
        assert wav.getframerate() == PCM_RATE and wav.getnframes() > PCM_RATE * 2
    assert (await other.get(f"{API}/{episode}/audio")).status_code == 404
    assert (
        await owner.post(f"{API}/{fallback}/quiz", json={"choices": [1, 1, 1]})
    ).status_code == 404


async def test_short_episode_keeps_the_transcript_without_publishing_audio(
    app: FastAPI, client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    from app.agents.graphs.podcast import PodcastDraft

    with pytest.raises(ValidationError):
        PodcastDraft.model_validate(SCRIPT.model_dump())

    uid = str(app.state.local_user_id)
    runtime: PodcastRuntime = app.state.daily.podcast
    runtime.speech = Voices("unused", [], seconds=1)
    episode = await _seed(runtime, db_session, uid)
    today = (await client.get(f"{API}/today")).json()
    assert (today["id"], today["status"]) == (episode, "transcript")
    assert (await client.get(f"{API}/{episode}/audio")).status_code == 404
