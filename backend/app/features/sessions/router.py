"""Sessions d'agents (SPEC 14.1). Toute action passe par REST ; le WebSocket ne fait que diffuser
les événements (serveur → client)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, WebSocket
from fastapi import status as http

from app.agents.runtime.events import SessionEvent
from app.core.deps import CurrentUserDep, Db, RuntimeDep
from app.features.sessions.schemas import (
    MessageRequest,
    ResumeRequest,
    SessionStatus,
    SessionView,
    StartSessionRequest,
    StartSessionResponse,
)
from app.features.sessions.service import SessionsService
from app.realtime.websocket import check_origin, serve_session_stream

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _service(current: CurrentUserDep, db: Db, runtime: RuntimeDep) -> SessionsService:
    return SessionsService(db, current.id, runtime)


Service = Annotated[SessionsService, Depends(_service)]


@router.post("", status_code=http.HTTP_202_ACCEPTED, response_model=StartSessionResponse)
async def start_session(body: StartSessionRequest, service: Service) -> StartSessionResponse:
    return StartSessionResponse(session_id=await service.start(body))


@router.get("", response_model=list[SessionView])
async def list_sessions(
    service: Service, graph: str | None = None, status: SessionStatus | None = None
) -> list[SessionView]:
    return await service.list(graph, status)


@router.get("/{session_id}", response_model=SessionView)
async def get_session(session_id: str, service: Service) -> SessionView:
    return await service.get(session_id)


@router.post("/{session_id}/resume", status_code=http.HTTP_202_ACCEPTED, response_model=SessionView)
async def resume_session(session_id: str, body: ResumeRequest, service: Service) -> SessionView:
    return await service.resume(session_id, body)


@router.post(
    "/{session_id}/message", status_code=http.HTTP_201_CREATED, response_model=SessionEvent
)
async def post_message(session_id: str, body: MessageRequest, service: Service) -> SessionEvent:
    return await service.message(session_id, body.text)


@router.post("/{session_id}/pause", response_model=SessionView)
async def pause_session(session_id: str, service: Service) -> SessionView:
    return await service.pause(session_id)


@router.post("/{session_id}/cancel", response_model=SessionView)
async def cancel_session(session_id: str, service: Service) -> SessionView:
    return await service.cancel(session_id)


@router.websocket("/{session_id}/stream", dependencies=[Depends(check_origin)])
async def stream_session(
    ws: WebSocket,
    session_id: str,
    current: CurrentUserDep,
    runtime: RuntimeDep,
    after_seq: Annotated[int, Query(ge=0)] = 0,
) -> None:
    """Rejoue les événements `seq > after_seq` puis diffuse le direct ; 4404 si la session est
    inconnue ou d'un autre utilisateur ; les messages du client sont ignorés."""
    await serve_session_stream(ws, runtime, current.id, session_id, after_seq)
