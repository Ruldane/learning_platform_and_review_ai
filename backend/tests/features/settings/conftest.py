from collections.abc import Callable

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.deps import get_providers
from app.core.providers import Providers
from app.core.security import Cipher
from app.features.settings.keys_service import ApiKeyService, DbKeyReader
from app.features.settings.service import SettingsModelReader
from app.providers.llm.factory import LlmFactory
from app.providers.llm.fake import FakeLlmProvider
from app.providers.search.brave import BraveKeyProvider

USER_ID = "u1"
# Seule clé Brave acceptée par le faux service (MockTransport) : aucune requête ne sort.
VALID_BRAVE_KEY = "BSA-valid-key-0001"


def _fake_brave_api(request: httpx.Request) -> httpx.Response:
    if request.headers.get("X-Subscription-Token") != VALID_BRAVE_KEY:
        return httpx.Response(401, json={"error": {"code": "SUBSCRIPTION_TOKEN_INVALID"}})
    return httpx.Response(200, json={"web": {"results": []}})


class ListingProvider(FakeLlmProvider):
    """Faux fournisseur qui sait lister des modèles, ou échouer en le faisant."""

    def __init__(self, models: list[str] | None, *, fail: bool = False) -> None:
        super().__init__([])
        self._models = models
        self._fail = fail

    async def list_models(self, api_key: str) -> list[str] | None:
        if self._fail:
            raise RuntimeError(f"échec réseau avec {api_key}")
        return self._models


@pytest.fixture
def fake_provider() -> FakeLlmProvider:
    return FakeLlmProvider([])


@pytest.fixture
def providers(
    db_session_factory: async_sessionmaker[AsyncSession], fake_provider: FakeLlmProvider
) -> Providers:
    cipher = Cipher(Fernet.generate_key())
    env_keys: dict[str, str | None] = {}
    llm = {"fake": fake_provider}
    keys = DbKeyReader(db_session_factory, cipher, env_keys)
    factory = LlmFactory(SettingsModelReader(db_session_factory), keys, llm, {})
    brave = BraveKeyProvider(httpx.AsyncClient(transport=httpx.MockTransport(_fake_brave_api)))
    return Providers(
        llm=llm,
        llm_factory=factory,
        cipher=cipher,
        env_keys=env_keys,
        key_providers={**llm, "brave": brave},
    )


@pytest.fixture
def app(app: FastAPI, providers: Providers) -> FastAPI:
    # Le faux fournisseur remplace les vrais : aucun appel réseau, clé de test maîtrisée.
    app.dependency_overrides[get_providers] = lambda: providers
    return app


@pytest.fixture
def swap_cipher(providers: Providers) -> Callable[[], None]:
    """Simule un secret d'application régénéré : un autre chiffreur remplace l'ancien."""

    def swap() -> None:
        providers.cipher = Cipher(Fernet.generate_key())

    return swap


@pytest.fixture
def service_with_env(
    db_session: AsyncSession, providers: Providers
) -> Callable[[dict[str, str | None]], ApiKeyService]:
    def make(env_keys: dict[str, str | None]) -> ApiKeyService:
        return ApiKeyService(
            db_session,
            USER_ID,
            providers.cipher,
            env_keys,
            providers.key_providers,
            llm=providers.llm,
        )

    return make
