"""Construct chat models for agents through a single factory."""

from collections.abc import Mapping

from langchain_core.language_models import BaseChatModel

from app.core.errors import AppError
from app.core.played import run_source
from app.core.security import SecretUnreadable
from app.providers.llm.base import (
    CALL_DEADLINE_KEY,
    LLM_CALL_DEADLINE_S,
    KeyReader,
    LlmProvider,
    ModelChoice,
    ModelChoiceReader,
    Tier,
)
from app.providers.llm.forcing import forced_choice

_SETTINGS_PLACE = "Settings > Models and keys"


class LlmFactory:
    def __init__(
        self,
        choices: ModelChoiceReader,
        keys: KeyReader,
        providers: Mapping[str, LlmProvider],
        base_urls: Mapping[str, str],
        *,
        call_deadline_s: float = LLM_CALL_DEADLINE_S,
    ) -> None:
        """Set the total deadline for each call made by a model built here."""
        self._choices = choices
        self._keys = keys
        self._providers = providers
        self._base_urls = base_urls
        self._call_deadline_s = call_deadline_s

    async def resolve(self, user_id: str, tier: Tier, agent: str | None = None) -> ModelChoice:
        """Use the agent override or tier choice, then apply any provider forced for this run."""
        choice = await self._choices.get_model_choice(user_id, tier, agent)
        provider = run_source(user_id)[1]
        return choice if provider is None else forced_choice(choice, provider, tier)

    async def get_chat_model(
        self, user_id: str, tier: Tier, agent: str | None = None
    ) -> BaseChatModel:
        choice = await self.resolve(user_id, tier, agent)
        provider = self._providers.get(choice.provider)
        if provider is None:
            raise AppError(
                "llm_provider_unknown",
                f"The provider {choice.provider} is unsupported.",
                400,
                {"provider": choice.provider},
            )
        key = await self._read_key(user_id, tier, provider)
        model = provider.build(choice.model, key, base_url=self._base_urls.get(provider.name))
        # Each call builds a fresh model with its own metadata and deadline.
        model.metadata = {**(model.metadata or {}), CALL_DEADLINE_KEY: self._call_deadline_s}
        return model

    async def _read_key(self, user_id: str, tier: Tier, provider: LlmProvider) -> str:
        try:
            key = await self._keys.get_key(user_id, provider.name)
        except SecretUnreadable as exc:
            raise AppError(
                "llm_key_unreadable",
                f"The saved {provider.label} API key could not be read. "
                f"Enter it again in {_SETTINGS_PLACE}.",
                400,
                {"provider": provider.name},
            ) from exc
        if not key:
            raise AppError(
                "llm_key_missing",
                f"No {provider.label} API key is configured for the {tier} tier. "
                f"Add one in {_SETTINGS_PLACE}.",
                400,
                {"provider": provider.name, "tier": tier},
            )
        return key
