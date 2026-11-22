"""Synthèse OpenAI Realtime côté serveur. Aucun secret dans les événements ou les erreurs."""

import asyncio
import base64
from binascii import Error as InvalidBase64
from collections.abc import AsyncIterable
from typing import Literal

from openai import AsyncOpenAI, OpenAIError
from openai.types.realtime import RealtimeServerEvent
from websockets.exceptions import WebSocketException

from app.providers.llm.base import KeyReader
from app.providers.speech.base import PCM_RATE, PCM_WIDTH, Speaker, SpeechUnavailable

SPEECH_MODEL = "gpt-realtime-2.1-mini"
PCM_LIMIT = 8 * 1024 * 1024
VOICES: dict[Speaker, Literal["marin", "cedar"]] = {"host": "marin", "coach": "cedar"}
_PROMPT = (
    "Lis le texte transmis mot pour mot dans sa langue, avec une voix naturelle et claire. "
    "Adopte un débit posé, autour de 145 mots par minute. "
    "Respecte chaque phrase et rends uniquement la lecture du texte transmis."
)


async def receive_pcm(events: AsyncIterable[RealtimeServerEvent]) -> bytes:
    audio = bytearray()
    async for event in events:
        if event.type == "error":
            raise SpeechUnavailable()
        if event.type == "response.output_audio.delta":
            try:
                audio.extend(base64.b64decode(event.delta, validate=True))
            except InvalidBase64:
                raise SpeechUnavailable() from None
            if len(audio) > PCM_LIMIT:
                raise SpeechUnavailable()
        if event.type == "response.done":
            if event.response.status == "completed" and audio and len(audio) % PCM_WIDTH == 0:
                return bytes(audio)
            raise SpeechUnavailable()
    raise SpeechUnavailable()


class OpenAIRealtimeSpeech:
    def __init__(self, keys: KeyReader) -> None:
        self._keys = keys

    async def speak(self, user_id: str, speaker: Speaker, text: str) -> bytes:
        key = await self._keys.get_key(user_id, "openai")
        if not key:
            raise SpeechUnavailable()
        try:
            async with (
                asyncio.timeout(90),
                AsyncOpenAI(api_key=key, max_retries=0) as client,
                client.realtime.connect(model=SPEECH_MODEL) as connection,
            ):
                await connection.session.update(
                    session={
                        "type": "realtime",
                        "audio": {
                            "output": {
                                "format": {"type": "audio/pcm", "rate": PCM_RATE},
                                "voice": VOICES[speaker],
                            }
                        },
                        "output_modalities": ["audio"],
                    }
                )
                await connection.response.create(
                    response={
                        "conversation": "none",
                        "instructions": _PROMPT,
                        "input": [
                            {
                                "type": "message",
                                "role": "user",
                                "content": [{"type": "input_text", "text": text}],
                            }
                        ],
                    }
                )
                return await receive_pcm(connection)
        except (OpenAIError, WebSocketException, OSError, TimeoutError):
            raise SpeechUnavailable() from None
