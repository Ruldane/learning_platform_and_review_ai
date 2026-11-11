from collections.abc import Callable

import pytest
from cryptography.fernet import Fernet
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bootstrap import Providers
from app.core.deps import get_providers
from app.core.security import Cipher
from app.features.settings.keys_service import ApiKeyService, DbKeyReader
from app.features.settings.service import SettingsModelReader
from app.providers.llm.factory import LlmFactory
from app.providers.llm.fake import FakeLlmProvider

USER_ID = "u1"


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
    return Providers(llm=llm, llm_factory=factory, cipher=cipher, env_keys=env_keys)


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
        return ApiKeyService(db_session, USER_ID, providers.cipher, env_keys, providers.llm)

    return make
