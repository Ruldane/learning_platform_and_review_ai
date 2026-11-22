from typing import Final, Literal, Protocol

from app.core.errors import AppError

PCM_RATE: Final = 24_000
PCM_WIDTH = 2
type Speaker = Literal["host", "coach"]


class SpeechUnavailable(AppError):
    def __init__(self) -> None:
        super().__init__("speech_unavailable", "La synthèse vocale est indisponible.", 503)


class SpeechProvider(Protocol):
    async def speak(self, user_id: str, speaker: Speaker, text: str) -> bytes:
        """Rend un seul segment PCM 16 bits, mono, à 24 kHz."""
        ...
