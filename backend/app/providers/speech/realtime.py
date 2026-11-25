"""OpenAI Realtime speech synthesis on the server side. No secret in the events or the errors."""

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
    "Read the supplied text word for word, in its own language, with a natural and clear voice. "
    "Adopt a measured pace, around 145 words per minute. "
    "Respect every sentence and return only the reading of the supplied text."
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
