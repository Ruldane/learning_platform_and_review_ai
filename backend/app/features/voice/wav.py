"""Validation of the format, the sample count and the bytes actually received."""

import wave
from io import BytesIO
from struct import error as StructError

from app.core.errors import AppError
from app.providers.speech.base import (
    PCM_WIDTH,
    RECORDING_LIMIT,
    RECORDING_RATE,
    RECORDING_SECONDS,
)


def pack_wav(frames: bytes, rate: int) -> bytes:
    output = BytesIO()
    with wave.open(output, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(PCM_WIDTH)
        audio.setframerate(rate)
        audio.writeframes(frames)
    return output.getvalue()


def _invalid() -> AppError:
    return AppError("voice_invalid_recording", "The audio recording is unreadable.", 422)


def validate_recording(raw: bytes) -> bytes:
    if len(raw) > RECORDING_LIMIT:
        raise AppError("voice_recording_too_large", "Recording too large.", 413)
    try:
        with wave.open(BytesIO(raw), "rb") as audio:
            channels, width, rate, samples, compression, _ = audio.getparams()
            if (channels, width, rate, compression) != (1, PCM_WIDTH, RECORDING_RATE, "NONE"):
                raise _invalid()
            if samples > RECORDING_RATE * RECORDING_SECONDS:
                raise AppError(
                    "voice_recording_too_long", "Enregistre 60 secondes au maximum.", 422
                )
            pcm = audio.readframes(samples)
            if not pcm or len(pcm) != samples * PCM_WIDTH:
                raise _invalid()
    except (EOFError, wave.Error, StructError):
        raise _invalid() from None
    return pack_wav(pcm, RECORDING_RATE)
