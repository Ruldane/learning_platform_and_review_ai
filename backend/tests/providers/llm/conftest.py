from collections.abc import Callable

import pytest

from app.core.security import SecretUnreadable
from app.providers.llm.base import ModelChoice, Tier
from app.providers.llm.factory import LlmFactory
from app.providers.llm.fake import FakeLlmProvider

Pair = tuple[str, str]


class _Choices:
    def __init__(self, tiers: dict[Tier, Pair], overrides: dict[str, Pair]) -> None:
        self._tiers = tiers
        self._overrides = overrides

    async def get_model_choice(self, user_id: str, tier: Tier, agent: str | None) -> ModelChoice:
        provider, model = self._overrides.get(agent or "", self._tiers[tier])
        return ModelChoice(provider=provider, model=model)


class _Keys:
    def __init__(self, keys: dict[str, str] | type[SecretUnreadable]) -> None:
        self._keys = keys

    async def get_key(self, user_id: str, provider: str) -> str | None:
        if isinstance(self._keys, type):
            raise self._keys()
        return self._keys.get(provider)


@pytest.fixture
def fake_provider() -> FakeLlmProvider:
    return FakeLlmProvider(["Bonjour tout le monde", "Deuxième réponse"])


@pytest.fixture
def factory_with(fake_provider: FakeLlmProvider) -> Callable[..., LlmFactory]:
    def build(
        *,
        tiers: dict[Tier, Pair],
        keys: dict[str, str] | type[SecretUnreadable],
        overrides: dict[str, Pair] | None = None,
        base_urls: dict[str, str] | None = None,
    ) -> LlmFactory:
        return LlmFactory(
            _Choices(tiers, overrides or {}),
            _Keys(keys),
            {"fake": fake_provider},
            base_urls or {},
        )

    return build
