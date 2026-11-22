from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.features.mcp.service import TokenService
from app.features.message_review.service import telegram_connection
from app.features.surprise_interview.repository import SettingsRepository
from app.features.surprise_interview.schemas import (
    SurprisePreferences,
    SurpriseSettingsOut,
    SurpriseTokenOption,
)

FEATURE = "surprise_interview"


async def get(db: AsyncSession, user_id: str) -> SurpriseSettingsOut:
    consent = await SettingsRepository(db, user_id).mine()
    link = await telegram_connection(db, user_id)
    tokens = await TokenService(db, user_id).dedicated_writers(FEATURE)
    return SurpriseSettingsOut(
        enabled=bool(
            consent and consent.enabled and link and consent.chat_consent_id == link.consent_id
        ),
        token_id=consent.token_id if consent else None,
        role=consent.role if consent else "",
        telegram_ready=link is not None,
        start=link.start if link else None,
        end=link.end if link else None,
        timezone=link.timezone if link else None,
        tokens=[SurpriseTokenOption(id=token.id, label=token.label) for token in tokens],
    )


async def put(
    db: AsyncSession, user_id: str, preferences: SurprisePreferences
) -> SurpriseSettingsOut:
    link = await telegram_connection(db, user_id)
    if preferences.enabled:
        if link is None:
            raise AppError(
                "surprise_telegram_required", "Associe d’abord ta discussion Telegram.", 409
            )
        if not preferences.role:
            raise AppError("surprise_role_required", "Indique le poste à préparer.", 422)
        tokens = await TokenService(db, user_id).dedicated_writers(FEATURE)
        if all(token.id != preferences.token_id for token in tokens):
            raise AppError("surprise_token_unavailable", "Choisis un jeton Nod dédié actif.", 404)
    else:
        preferences = preferences.model_copy(update={"token_id": None})
    await SettingsRepository(db, user_id).save(
        preferences, link.consent_id if preferences.enabled and link else None
    )
    return await get(db, user_id)
