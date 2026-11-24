import logging
from typing import Any

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.run_settings import RunSettings
from app.features.settings.delays import DEFAULT_DELAYS as DEFAULT_DELAYS
from app.features.settings.delays import validated_delays as validated_delays
from app.features.settings.repository import UserSettingsRepository, onboarded_user_ids
from app.features.settings.schemas import UserSettings, is_overridable
from app.providers.llm.base import ModelChoice, Tier

logger = logging.getLogger(__name__)

# Computed fields are recomputed on read: they are not stored.
_COMPUTED = {"availability": {"weekly_budget_minutes"}}


def _has_removed_agents(stored: dict[str, Any]) -> bool:
    overrides = stored.get("agent_overrides")
    return isinstance(overrides, dict) and not all(is_overridable(name) for name in overrides)


def _without_removed_agents(stored: dict[str, Any]) -> dict[str, Any]:
    """Removes from a stored override an agent that is no longer in the catalog (renamed,
    deleted, demo): the other overrides stay. Logs nothing: settings are read on every model
    call; `SettingsService.replace` says it once, when saving."""
    if not _has_removed_agents(stored):
        return stored
    overrides: dict[str, Any] = stored["agent_overrides"]
    kept = {name: choice for name, choice in overrides.items() if is_overridable(name)}
    return {**stored, "agent_overrides": kept}


def _parse_stored(stored: dict[str, Any]) -> UserSettings:
    """Defaults merged with what is stored. Unknown keys are ignored (backward
    compatibility); an invalid field falls back to its default without failing the read."""
    stored = _without_removed_agents(stored)
    try:
        return UserSettings.model_validate(stored)
    except ValidationError as exc:
        invalid = {str(err["loc"][0]) for err in exc.errors() if err["loc"]}
        # Only field names are logged, never their content.
        logger.warning("Invalid stored settings, default values for: %s", sorted(invalid))
        kept = {key: value for key, value in stored.items() if key not in invalid}
        try:
            return UserSettings.model_validate(kept)
        except ValidationError:
            return UserSettings()


async def scheduled_users(db: AsyncSession) -> list[str]:
    """The accounts whose first run is done (`onboarding_done` of `GET /settings`, D183),
    oldest first: scheduled jobs that may call a model or the web only work for them (D197).
    Read without `user_id`, identifiers only."""
    return await onboarded_user_ids(db)


class SettingsService:
    def __init__(self, session: AsyncSession, user_id: str) -> None:
        self._repo = UserSettingsRepository(session, user_id)

    async def get(self, *, initialize: bool = False) -> UserSettings:
        """The stored settings, defaults merged; performs no write, except `initialize`.

        `initialize` (reserved for `GET /settings` and `replace`): on the very first access of an
        account without a settings row, creates the row that sets `onboarding_done`: true if the
        account already has an API key or a goal (account from before phase 9, D183), false
        otherwise. The decision is made once and never redone: a key added during the first run
        does not end it. Other readers (other features, agents, scheduled jobs) do not pass
        `initialize`: a write inside their read would hold the database write lock while
        another session writes.
        """
        stored = await self._repo.get_data()
        if stored is None and initialize:
            stored = await self._repo.initialize(
                {"onboarding_done": await self._repo.has_prior_data()}
            )
        return _parse_stored(stored if isinstance(stored, dict) else {})

    async def close_local_claim(self) -> None:
        """Closes the local space takeover for good (reserved key of these settings, which
        survives every replacement; never exposed by the API)."""
        await self._repo.close_local_claim()

    async def replace(self, new: UserSettings) -> UserSettings:
        """Saves the settings. `onboarding_done` never goes back to false: a page that sends
        back the old setting (or forgets it) does not reopen the first run (P20). The repository
        writes it monotonically (no read then write): even two crossing requests do not undo
        it; the response says what is saved."""
        current = await self.get(initialize=True)
        stored = await self._repo.get_data() or {}
        if _has_removed_agents(stored):
            # Once, here: the override of a removed agent goes away with this replacement.
            logger.warning("Settings saved: override of a removed agent dropped (agent_overrides)")
        done = current.onboarding_done or new.onboarding_done
        kept = new.model_copy(update={"onboarding_done": done})
        await self._repo.save_data(kept.model_dump(mode="json", exclude=_COMPUTED))
        saved = await self._repo.get_data() or {}
        return kept.model_copy(update={"onboarding_done": bool(saved.get("onboarding_done", done))})


class SettingsModelReader:
    """Reads the model to use, for the LLM factory. Opens its own session: it is called
    outside any HTTP request (agents, scheduled jobs)."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_model_choice(self, user_id: str, tier: Tier, agent: str | None) -> ModelChoice:
        async with self._session_factory() as session:
            settings = await SettingsService(session, user_id).get()
        if agent is not None and agent in settings.agent_overrides:
            return settings.agent_overrides[agent]
        return settings.tiers[tier]


class SettingsRunReader:
    """Settings of an agent run (`RunSettingsSource` of the engine), assembled by
    `app.bootstrap`. Opens its own session: called by the runner, outside any HTTP request."""

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
