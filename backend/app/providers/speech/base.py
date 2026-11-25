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
        super().__init__("speech_unavailable", "Speech synthesis is unavailable.", 503)


class SpeechProvider(Protocol):
    async def speak(self, user_id: str, speaker: Speaker, text: str) -> bytes:
        """Returns a single PCM segment, 16-bit, mono, at 24 kHz."""
        ...


class TranscriptionUnavailable(AppError):
    def __init__(self) -> None:
        super().__init__(
            "transcription_unavailable", "Transcription is unavailable. You can type instead.", 503
        )


class TranscriptionProvider(Protocol):
    async def transcribe(self, user_id: str, wav: bytes) -> str:
        """Reads a mono PCM WAV recording already bounded and checked by the service."""
        ...
