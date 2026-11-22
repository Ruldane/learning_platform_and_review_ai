"""Transcription de clips WAV via la clé du compte. Aucun journal audio ou texte."""

import asyncio

from openai import AsyncOpenAI, OpenAIError

from app.providers.llm.base import KeyReader
from app.providers.speech.base import TranscriptionUnavailable

TRANSCRIPTION_MODEL = "gpt-transcribe"


class OpenAITranscription:
    def __init__(self, keys: KeyReader) -> None:
        self._keys = keys

    async def transcribe(self, user_id: str, wav: bytes) -> str:
        key = await self._keys.get_key(user_id, "openai")
        if not key:
            raise TranscriptionUnavailable()
        try:
            async with (
                asyncio.timeout(40),
                AsyncOpenAI(api_key=key, max_retries=0) as client,
            ):
                transcript = await client.audio.transcriptions.create(
                    model=TRANSCRIPTION_MODEL,
                    file=("recording.wav", wav, "audio/wav"),
                    response_format="json",
                )
        except (OpenAIError, OSError, TimeoutError):
            raise TranscriptionUnavailable() from None
        return transcript.text
