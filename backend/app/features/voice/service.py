from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from app.core.errors import AppError
from app.features.voice.schemas import MAX_TRANSCRIPT, VoiceTranscript
from app.features.voice.wav import pack_wav, validate_recording
from app.providers.speech.base import (
    PCM_RATE,
    PCM_WIDTH,
    SpeechProvider,
    SpeechUnavailable,
    TranscriptionProvider,
)

_MAX_SPOKEN_PCM = 8 * 1024 * 1024


class VoiceService:
    def __init__(self, transcription: TranscriptionProvider, speech: SpeechProvider) -> None:
        self.transcription = transcription
        self.speech = speech
        self._active: set[str] = set()

    @asynccontextmanager
    async def _reserve(self, user_id: str) -> AsyncIterator[None]:
        if user_id in self._active:
            raise AppError("voice_busy", "Une opération audio est déjà en cours.", 409)
        self._active.add(user_id)
        try:
            yield
        finally:
            self._active.discard(user_id)

    async def transcribe(self, user_id: str, raw: bytes) -> VoiceTranscript:
        recording = validate_recording(raw)
        async with self._reserve(user_id):
            text = (await self.transcription.transcribe(user_id, recording)).strip()
        if not text:
            raise AppError("voice_no_speech", "Aucune parole reconnue. Tu peux écrire.", 422)
        return VoiceTranscript(text=text[:MAX_TRANSCRIPT])

    async def speak(self, user_id: str, text: str) -> bytes:
        clean = text.strip()
        if not clean:
            raise AppError("voice_empty_text", "Le texte à lire est vide.", 422)
        async with self._reserve(user_id):
            pcm = await self.speech.speak(user_id, "coach", clean)
        if not pcm or len(pcm) % PCM_WIDTH or len(pcm) > _MAX_SPOKEN_PCM:
            raise SpeechUnavailable()
        return pack_wav(pcm, PCM_RATE)
