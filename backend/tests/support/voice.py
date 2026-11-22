import wave
from io import BytesIO


def sample_wav(frames: int = 1600) -> bytes:
    output = BytesIO()
    with wave.open(output, "wb") as audio:
        audio.setparams((1, 2, 16_000, frames, "NONE", ""))
        audio.writeframes(b"\x10\x00" * frames)
    return output.getvalue()


class VoiceDouble:
    def __init__(self, text: str = "Une explication dictée à vérifier.") -> None:
        self.calls: list[tuple[str, int]] = []
        self.text = text

    async def transcribe(self, user_id: str, data: bytes) -> str:
        with wave.open(BytesIO(data), "rb") as audio:
            assert audio.getnframes() > 0 and audio.getframerate() == 16_000
        self.calls.append((user_id, len(data)))
        return self.text

    async def speak(self, user_id: str, speaker: str, text: str) -> bytes:
        assert speaker == "coach"
        self.calls.append((user_id, len(text)))
        return bytes(4800)
