import logging
from typing import Any

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.run_settings import RunSettings
from app.features.settings.repository import UserSettingsRepository
from app.features.settings.schemas import UserSettings
from app.providers.llm.base import ModelChoice, Tier

logger = logging.getLogger(__name__)

# Les champs calculés sont recalculés à la lecture : on ne les stocke pas.
_COMPUTED = {"availability": {"weekly_budget_minutes"}}


def _parse_stored(stored: dict[str, Any]) -> UserSettings:
    """Défauts fusionnés avec le stocké. Les clés inconnues sont ignorées (compatibilité
    ascendante) ; un champ invalide retombe sur son défaut sans faire échouer la lecture."""
    try:
        return UserSettings.model_validate(stored)
    except ValidationError as exc:
        invalid = {str(err["loc"][0]) for err in exc.errors() if err["loc"]}
        # Seuls les noms de champs sont journalisés, jamais leur contenu.
        logger.warning("Réglages stockés invalides, valeurs par défaut pour : %s", sorted(invalid))
        kept = {key: value for key, value in stored.items() if key not in invalid}
        try:
            return UserSettings.model_validate(kept)
        except ValidationError:
            return UserSettings()


class SettingsService:
    def __init__(self, session: AsyncSession, user_id: str) -> None:
        self._repo = UserSettingsRepository(session, user_id)

    async def get(self) -> UserSettings:
        stored = await self._repo.get_data()
        return _parse_stored(stored if isinstance(stored, dict) else {})

    async def replace(self, new: UserSettings) -> UserSettings:
        await self._repo.save_data(new.model_dump(mode="json", exclude=_COMPUTED))
        return new


class SettingsModelReader:
    """Lecture du modèle à utiliser, pour la fabrique LLM. Ouvre sa propre session : elle est
    appelée hors requête HTTP (agents, tâches planifiées)."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_model_choice(self, user_id: str, tier: Tier, agent: str | None) -> ModelChoice:
        async with self._session_factory() as session:
            settings = await SettingsService(session, user_id).get()
        if agent is not None and agent in settings.agent_overrides:
            return settings.agent_overrides[agent]
        return settings.tiers[tier]


class SettingsRunReader:
    """Réglages d'une exécution d'agents (`RunSettingsSource` du moteur), assemblé par
    `app.bootstrap`. Ouvre sa propre session : appelé par le runner, hors requête HTTP."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_run_settings(self, user_id: str) -> RunSettings:
        async with self._session_factory() as session:
            settings = await SettingsService(session, user_id).get()
        return RunSettings(
            session_token_cap=settings.session_token_cap,
            debate_rounds=settings.debate_rounds,
            lesson_language=settings.lesson_language,
            search_languages=tuple(settings.search_languages),
            style_guide=settings.style_guide,
        )
