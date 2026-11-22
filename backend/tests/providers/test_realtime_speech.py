import base64
from collections.abc import AsyncIterator

import pytest
from openai.types.realtime import (
    RealtimeResponse,
    RealtimeServerEvent,
    ResponseAudioDeltaEvent,
    ResponseDoneEvent,
)

from app.providers.speech.base import SpeechUnavailable
from app.providers.speech.realtime import receive_pcm


async def events(*, complete: bool = True) -> AsyncIterator[RealtimeServerEvent]:
    for offset, pcm in enumerate((b"\x00\x01", b"\x02\x03")):
        yield ResponseAudioDeltaEvent(
            type="response.output_audio.delta",
            event_id=f"audio-{offset}",
            item_id="item",
            response_id="response",
            content_index=0,
            output_index=0,
            delta=base64.b64encode(pcm).decode(),
        )
    yield ResponseDoneEvent(
        type="response.done",
        event_id="done",
        response=RealtimeResponse(status="completed" if complete else "failed"),
    )


async def test_receives_ordered_pcm_and_rejects_incomplete_audio() -> None:
    assert await receive_pcm(events()) == b"\x00\x01\x02\x03"
    with pytest.raises(SpeechUnavailable):
        await receive_pcm(events(complete=False))
