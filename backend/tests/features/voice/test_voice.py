import httpx
from fastapi import FastAPI

from tests.support.voice import VoiceDouble, sample_wav

PREFIX = "/api/v1/voice"
WAV_HEADERS = {"content-type": "audio/wav"}


async def test_transcribes_a_bounded_clip_for_the_current_account(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    double = VoiceDouble()
    app.state.voice.transcription = double
    clip = sample_wav()
    reply = await client.post(f"{PREFIX}/transcriptions", content=clip, headers=WAV_HEADERS)
    assert reply.status_code == 200, reply.text
    assert reply.json() == {"text": "Une explication dictée à vérifier."}
    assert reply.headers["cache-control"] == "no-store"
    assert double.calls == [(app.state.local_user_id, len(clip))]


async def test_rejects_invalid_audio(client: httpx.AsyncClient) -> None:
    reply = await client.post(
        f"{PREFIX}/transcriptions",
        content=b"texte",
        headers=WAV_HEADERS,
    )
    assert reply.status_code == 422, reply.text
    assert reply.json()["error"]["code"] == "voice_invalid_recording"


async def test_clip_duration_is_checked_against_wav_samples(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    double = VoiceDouble()
    app.state.voice.transcription = double
    reply = await client.post(
        f"{PREFIX}/transcriptions", content=sample_wav(16_000 * 60 + 1), headers=WAV_HEADERS
    )
    assert reply.status_code == 422, reply.text
    assert reply.json()["error"]["code"] == "voice_recording_too_long" and not double.calls


async def test_rejects_large_bodies_before_audio_parsing(client: httpx.AsyncClient) -> None:
    reply = await client.post(
        f"{PREFIX}/transcriptions", content=bytes(2 * 1024 * 1024 + 1), headers=WAV_HEADERS
    )
    assert reply.status_code == 413 and reply.json()["error"]["code"] == "voice_recording_too_large"
