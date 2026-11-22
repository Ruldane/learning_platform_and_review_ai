import wave
from io import BytesIO

from fastapi import FastAPI

from tests.isolation.conftest import Browser
from tests.support.voice import VoiceDouble, sample_wav


async def test_voice_only_uses_the_authenticated_account(
    google_app: FastAPI, google_client_factory: Browser
) -> None:
    owner = await google_client_factory("voix-a@example.test")
    other = await google_client_factory("voix-b@example.test")
    owner_id = (await owner.get("/api/v1/auth/me")).json()["id"]
    other_id = (await other.get("/api/v1/auth/me")).json()["id"]
    voice = VoiceDouble()
    google_app.state.voice.transcription = google_app.state.voice.speech = voice
    clip = sample_wav()
    request = {"content": clip, "headers": {"content-type": "audio/wav"}}
    assert (await owner.post("/api/v1/voice/transcriptions", **request)).status_code == 200
    url = f"/api/v1/voice/transcriptions?user_id={owner_id}"
    second = await other.post(url, **request)
    assert second.status_code == 200
    spoken = await other.post(
        f"/api/v1/voice/speech?user_id={owner_id}", json={"text": "Question."}
    )
    assert spoken.status_code == 200 and spoken.headers["cache-control"] == "no-store"
    with wave.open(BytesIO(spoken.content), "rb") as audio:
        assert audio.getnframes() > 0 and audio.getframerate() == 24_000
    assert voice.calls == [
        (owner_id, len(clip)),
        (other_id, len(clip)),
        (other_id, len("Question.")),
    ]
