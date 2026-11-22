from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.core.caller import MCP_IDENTITY
from app.core.deps import Db, InterfaceUserDep, RuntimeDep
from app.core.errors import AppError
from app.core.field_paths import FieldPathsRoute
from app.features.applications.service.runtime import ApplicationsRuntime
from app.features.surprise_interview import preferences
from app.features.surprise_interview.schemas import (
    SurpriseAnswerIn,
    SurpriseAnswerOut,
    SurpriseChatId,
    SurpriseChatIn,
    SurpriseId,
    SurpriseInviteOut,
    SurprisePreferences,
    SurpriseSettingsOut,
    SurpriseStartOut,
    SurpriseStateOut,
)
from app.features.surprise_interview.service import SurpriseInterviews

router = APIRouter(
    prefix="/surprise-interviews", tags=["surprise_interview"], route_class=FieldPathsRoute
)


def _transport(request: Request, db: Db, runtime: RuntimeDep) -> SurpriseInterviews:
    actor = MCP_IDENTITY.get()
    if actor is None:
        raise AppError("surprise_nod_only", "Cette action est réservée au jeton Nod associé.", 403)
    rt: ApplicationsRuntime = request.app.state.career.applications
    return SurpriseInterviews(db, rt, actor, runtime.runner)


Transport = Annotated[SurpriseInterviews, Depends(_transport)]


@router.get("/settings")
async def surprise_settings(current: InterfaceUserDep, db: Db) -> SurpriseSettingsOut:
    return await preferences.get(db, current.id)


@router.put("/settings")
async def configure_surprise(
    body: SurprisePreferences, current: InterfaceUserDep, db: Db
) -> SurpriseSettingsOut:
    return await preferences.put(db, current.id, body)


@router.post("/invite")
async def surprise_invite(body: SurpriseChatIn, transport: Transport) -> SurpriseInviteOut:
    return await transport.invite(body.chat_id)


@router.post("/{invitation_id}/accept", status_code=202)
async def surprise_accept(
    invitation_id: SurpriseId, body: SurpriseChatIn, transport: Transport
) -> SurpriseStartOut:
    return await transport.accept(invitation_id, body.chat_id)


@router.get("/{invitation_id}")
async def surprise_state(
    invitation_id: SurpriseId, chat_id: Annotated[SurpriseChatId, Query()], transport: Transport
) -> SurpriseStateOut:
    return await transport.state(invitation_id, chat_id)


@router.post("/{invitation_id}/answer")
async def surprise_answer(
    invitation_id: SurpriseId, body: SurpriseAnswerIn, transport: Transport
) -> SurpriseAnswerOut:
    return await transport.answer(invitation_id, body)
