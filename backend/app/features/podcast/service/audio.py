"""Assemble the lines into mono WAV, in script order."""

import wave
from collections.abc import Sequence
from dataclasses import dataclass
from io import BytesIO

from app.agents.tools.podcast_port import PodcastLine
from app.providers.speech.base import PCM_RATE, PCM_WIDTH, SpeechProvider, SpeechUnavailable

_PAUSE = bytes(PCM_RATE * PCM_WIDTH // 4)
MAX_WAVE_BYTES = 50 * 1024 * 1024


@dataclass(frozen=True)
class EpisodeAudio:
    data: bytes
    duration_seconds: int


async def synthesize(
    voice: SpeechProvider, user_id: str, lines: Sequence[PodcastLine]
) -> EpisodeAudio:
    output = BytesIO()
    with wave.open(output, "wb") as media:
        media.setnchannels(1)
        media.setsampwidth(PCM_WIDTH)
        media.setframerate(PCM_RATE)
        for index, line in enumerate(lines):
            pcm = await voice.speak(user_id, line.speaker, line.text)
            pause = _PAUSE if index else b""
            total_bytes = output.tell() + len(pause) + len(pcm)
            if not pcm or len(pcm) % PCM_WIDTH or total_bytes > MAX_WAVE_BYTES:
                raise SpeechUnavailable()
            if pause:
                media.writeframesraw(pause)
            media.writeframesraw(pcm)
        seconds = round(media.getnframes() / PCM_RATE)
    return EpisodeAudio(output.getvalue(), seconds)
