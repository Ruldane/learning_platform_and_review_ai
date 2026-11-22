from typing import Final, Literal, Protocol

from app.core.errors import AppError

PCM_RATE: Final = 24_000
PCM_WIDTH = 2
RECORDING_RATE: Final = 16_000
RECORDING_SECONDS: Final = 60
RECORDING_LIMIT: Final = 2 * 1024 * 1024
type Speaker = Literal["host", "coach"]


class SpeechUnavailable(AppError):
    def __init__(self) -> None:
        super().__init__("speech_unavailable", "La synthèse vocale est indisponible.", 503)


class SpeechProvider(Protocol):
    async def speak(self, user_id: str, speaker: Speaker, text: str) -> bytes:
        """Rend un seul segment PCM 16 bits, mono, à 24 kHz."""
        ...


class TranscriptionUnavailable(AppError):
    def __init__(self) -> None:
        super().__init__(
            "transcription_unavailable", "La transcription est indisponible. Tu peux écrire.", 503
        )


class TranscriptionProvider(Protocol):
    async def transcribe(self, user_id: str, wav: bytes) -> str:
        """Lit un enregistrement WAV mono PCM déjà borné et contrôlé par le service."""
        ...
