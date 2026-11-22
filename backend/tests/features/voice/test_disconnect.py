import asyncio

import pytest
from starlette.types import Message

from app.core.errors import AppError
from app.features.voice.disconnect import until_disconnect
from app.features.voice.service import VoiceService
from tests.support.voice import VoiceDouble, sample_wav


class FirstCallWaits(VoiceDouble):
    def __init__(self) -> None:
        super().__init__()
        self.started = asyncio.Event()
        self.cancelled = asyncio.Event()

    async def transcribe(self, user_id: str, data: bytes) -> str:
        if not self.started.is_set():
            self.started.set()
            try:
                await asyncio.Future[None]()
            except asyncio.CancelledError:
                self.cancelled.set()
                raise
        return await super().transcribe(user_id, data)


async def test_disconnect_cancels_the_provider_and_releases_the_account() -> None:
    port = FirstCallWaits()
    service = VoiceService(port, port)

    async def disconnect() -> Message:
        await port.started.wait()
        return {"type": "http.disconnect"}

    with pytest.raises(AppError, match="Opération audio annulée"):
        await until_disconnect(disconnect, service.transcribe("compte-fictif", sample_wav()))
    assert port.cancelled.is_set()
    retried = await service.transcribe("compte-fictif", sample_wav())
    assert retried.text == port.text
