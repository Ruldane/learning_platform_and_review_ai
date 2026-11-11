"""Composition de l'application : l'unique module qui assemble les implémentations concrètes
(fournisseurs LLM) avec les features. Le lifespan l'appelle une fois au démarrage."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.core.providers import Providers
from app.core.security import Cipher
from app.features.settings.keys_service import DbKeyReader
from app.features.settings.service import SettingsModelReader
from app.providers.llm.base import LlmProvider
from app.providers.llm.factory import LlmFactory
from app.providers.llm.glm import GlmProvider
from app.providers.llm.registry import LLM_PROVIDERS


def build_providers(
    settings: Settings, session_factory: async_sessionmaker[AsyncSession], cipher: Cipher
) -> Providers:
    # GLM : l'adresse Z.ai configurée sert aussi au test de clé et à la liste des modèles.
    llm: dict[str, LlmProvider] = {
        **LLM_PROVIDERS,
        "glm": GlmProvider(base_url=settings.zai_base_url),
    }
    env_keys: dict[str, str | None] = {
        "anthropic": settings.anthropic_api_key,
        "openai": settings.openai_api_key,
        "glm": settings.zai_api_key,
    }
    factory = LlmFactory(
        SettingsModelReader(session_factory),
        DbKeyReader(session_factory, cipher, env_keys),
        llm,
        {"glm": settings.zai_base_url},
    )
    return Providers(llm=llm, llm_factory=factory, cipher=cipher, env_keys=env_keys)
