"""Fabrique de modèles de chat : l'unique point d'instanciation des LLM (aucun agent ne
construit de modèle ailleurs)."""

from collections.abc import Mapping

from langchain_core.language_models import BaseChatModel

from app.core.errors import AppError
from app.core.security import SecretUnreadable
from app.providers.llm.base import (
    KeyReader,
    LlmProvider,
    ModelChoice,
    ModelChoiceReader,
    Tier,
)

_SETTINGS_PLACE = "Réglages > Modèles et clés"


class LlmFactory:
    def __init__(
        self,
        choices: ModelChoiceReader,
        keys: KeyReader,
        providers: Mapping[str, LlmProvider],
        base_urls: Mapping[str, str],
    ) -> None:
        self._choices = choices
        self._keys = keys
        self._providers = providers
        self._base_urls = base_urls

    async def resolve(self, user_id: str, tier: Tier, agent: str | None = None) -> ModelChoice:
        """Fournisseur et modèle retenus : surcharge de l'agent si elle existe, sinon le niveau."""
        return await self._choices.get_model_choice(user_id, tier, agent)

    async def get_chat_model(
        self, user_id: str, tier: Tier, agent: str | None = None
    ) -> BaseChatModel:
        choice = await self.resolve(user_id, tier, agent)
        provider = self._providers.get(choice.provider)
        if provider is None:
            raise AppError(
                "llm_provider_unknown",
                f"Le fournisseur « {choice.provider} » n'est pas pris en charge.",
                400,
                {"provider": choice.provider},
            )
        key = await self._read_key(user_id, tier, provider)
        return provider.build(choice.model, key, base_url=self._base_urls.get(provider.name))

    async def _read_key(self, user_id: str, tier: Tier, provider: LlmProvider) -> str:
        try:
            key = await self._keys.get_key(user_id, provider.name)
        except SecretUnreadable as exc:
            raise AppError(
                "llm_key_unreadable",
                f"La clé {provider.label} enregistrée ne peut plus être lue. "
                f"Ressaisis-la dans {_SETTINGS_PLACE}.",
                400,
                {"provider": provider.name},
            ) from exc
        if not key:
            raise AppError(
                "llm_key_missing",
                f"Aucune clé {provider.label} n'est configurée pour le niveau « {tier} ». "
                f"Ajoute-la dans {_SETTINGS_PLACE}.",
                400,
                {"provider": provider.name, "tier": tier},
            )
        return key
