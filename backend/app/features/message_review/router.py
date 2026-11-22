from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.core.caller import MCP_IDENTITY, McpIdentity
from app.core.deps import Db, InterfaceUserDep
from app.core.errors import AppError
from app.core.field_paths import FieldPathsRoute
from app.features.message_review import preferences
from app.features.message_review.schemas import (
    ChatId,
    RecordId,
    TelegramAnswerIn,
    TelegramAnswerOut,
    TelegramClaimIn,
    TelegramClaimOut,
    TelegramRevealOut,
    TelegramReviewPreferences,
    TelegramReviewSettingsOut,
)
from app.features.message_review.service import TelegramReviews
from app.features.quiz.service.runtime import QuizRuntime

ROOT = "/message-reviews"
router = APIRouter(prefix=ROOT, tags=["message_review"], route_class=FieldPathsRoute)


def _actor() -> McpIdentity:
    identity = MCP_IDENTITY.get()
    if identity is None:
        raise AppError("telegram_nod_only", "Cette action est réservée au jeton Nod associé.", 403)
    return identity


def _transport(
    request: Request, db: Db, identity: Annotated[McpIdentity, Depends(_actor)]
) -> TelegramReviews:
    quiz: QuizRuntime = request.app.state.quiz
    return TelegramReviews(db, quiz, identity)


Transport = Annotated[TelegramReviews, Depends(_transport)]


@router.get("/settings")
async def read_settings(current: InterfaceUserDep, db: Db) -> TelegramReviewSettingsOut:
    return await preferences.get(db, current.id)


@router.put("/settings")
async def change_settings(
    body: TelegramReviewPreferences, current: InterfaceUserDep, db: Db
) -> TelegramReviewSettingsOut:
    return await preferences.set_preferences(db, current.id, body)


@router.post("/claim")
async def claim(body: TelegramClaimIn, transport: Transport) -> TelegramClaimOut:
    return await transport.claim(body.chat_id)


@router.get("/{challenge_id}/answer")
async def reveal(
    challenge_id: RecordId, chat_id: Annotated[ChatId, Query()], transport: Transport
) -> TelegramRevealOut:
    return await transport.reveal(challenge_id, chat_id)


@router.post("/{challenge_id}/answer")
async def answer(
    challenge_id: RecordId, body: TelegramAnswerIn, transport: Transport
) -> TelegramAnswerOut:
    return await transport.answer(challenge_id, body)
