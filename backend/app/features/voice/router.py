from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Request, Response
from starlette.requests import HTTPConnection

from app.core.deps import InterfaceUserDep
from app.features.voice.disconnect import until_disconnect
from app.features.voice.schemas import SpeechIn, VoiceTranscript
from app.features.voice.service import VoiceService

router = APIRouter(prefix="/voice", tags=["voice"])
_NO_STORE = {"Cache-Control": "no-store"}
_WAV_RESPONSE: dict[int | str, dict[str, Any]] = {
    200: {"content": {"audio/wav": {"schema": {"type": "string", "format": "binary"}}}}
}


def _service(conn: HTTPConnection) -> VoiceService:
    service: VoiceService = conn.app.state.voice
    return service


VoiceDep = Annotated[VoiceService, Depends(_service)]


@router.post("/transcriptions")
async def create_transcription(
    request: Request,
    response: Response,
    user: InterfaceUserDep,
    service: VoiceDep,
    recording: Annotated[
        bytes, Body(media_type="audio/wav", description="PCM mono 16 bits, 16 kHz, 60 s")
    ],
) -> VoiceTranscript:
    response.headers.update(_NO_STORE)
    return await until_disconnect(request.receive, service.transcribe(user.id, recording))


@router.post("/speech", response_class=Response, responses=_WAV_RESPONSE)
async def create_speech(
    request: Request, body: SpeechIn, user: InterfaceUserDep, service: VoiceDep
) -> Response:
    wav = await until_disconnect(request.receive, service.speak(user.id, body.text))
    return Response(wav, media_type="audio/wav", headers=_NO_STORE)
