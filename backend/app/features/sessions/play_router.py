from datetime import UTC, datetime

from fastapi import APIRouter, Request

from app.core.deps import CurrentUserDep, Db, RuntimeDep
from app.features.sessions.play_schemas import PlayBrief, PlayLaunch, PlayStart, PlaySubmit
from app.features.sessions.play_service import brief_view, expire_steps, owned_play
from app.features.sessions.schemas import StartSessionResponse
from app.mcp.played import play_identity
from app.mcp.registry import Registry

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("/play")
async def list_played(request: Request, current: CurrentUserDep) -> list[PlayLaunch]:
    identity = play_identity(current.id)
    registry: Registry = request.app.state.mcp_registry
    return [
        PlayLaunch(
            launch=tool.name,
            graph=graph,
            description=tool.summary or tool.description,
            input_schema=dict(tool.input_schema),
        )
        for tool, graph in registry.play_launches(identity)
    ]


@router.post("/play", status_code=202)
async def start_played(
    body: PlayStart, request: Request, current: CurrentUserDep
) -> StartSessionResponse:
    identity = play_identity(current.id, write=True)
    result = await request.app.state.mcp_play_launch(
        identity, body.launch, body.arguments, body.played_by
    )
    return StartSessionResponse.model_validate(result)


@router.get("/{session_id}/play")
async def read_played(
    session_id: str, current: CurrentUserDep, db: Db, request: Request
) -> PlayBrief:
    play_identity(current.id)
    await expire_steps(request.app.state.session_factory, datetime.now(UTC), user_id=current.id)
    return brief_view(await owned_play(request, db, current.id, session_id))


@router.post("/{session_id}/play", status_code=202)
async def submit_played(
    session_id: str,
    body: PlaySubmit,
    current: CurrentUserDep,
    db: Db,
    request: Request,
    runtime: RuntimeDep,
) -> StartSessionResponse:
    await owned_play(request, db, current.id, session_id, write=True)
    await runtime.runner.submit_step(current.id, session_id, body.step_id, body.response)
    return StartSessionResponse(session_id=session_id)
