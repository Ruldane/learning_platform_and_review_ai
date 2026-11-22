from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.features.mcp.service import TokenService
from app.features.message_review.repository import ConsentRepository
from app.features.message_review.schemas import (
    NodTokenOption,
    TelegramReviewPreferences,
    TelegramReviewSettingsOut,
)
from app.features.settings.service import SettingsService

FEATURE = "message_review"


async def _tokens(db: AsyncSession, user_id: str) -> list[NodTokenOption]:
    now = datetime.now(UTC)
    return [
        NodTokenOption(id=token.id, label=token.label)
        for token in await TokenService(db, user_id).mine()
        if token.mode == "write"
        and token.features == [FEATURE]
        and token.revoked_at is None
        and token.expires_at > now
    ]


async def get(db: AsyncSession, user_id: str) -> TelegramReviewSettingsOut:
    row = await ConsentRepository(db, user_id).mine()
    prefs = (
        TelegramReviewPreferences.model_validate(row)
        if row is not None
        else TelegramReviewPreferences()
    )
    return TelegramReviewSettingsOut(
        **prefs.model_dump(),
        timezone=(await SettingsService(db, user_id).get()).timezone,
        tokens=await _tokens(db, user_id),
    )


async def set_preferences(
    db: AsyncSession, user_id: str, preferences: TelegramReviewPreferences
) -> TelegramReviewSettingsOut:
    if preferences.enabled:
        if all(token.id != preferences.token_id for token in await _tokens(db, user_id)):
            raise AppError(
                "nod_token_unavailable",
                "Choisis un jeton Nod actif et limité à la révision par messagerie.",
                404,
            )
    else:
        preferences = preferences.model_copy(update={"token_id": None, "chat_id": None})
    await ConsentRepository(db, user_id).save(preferences.model_dump())
    return await get(db, user_id)
