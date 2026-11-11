import httpx
from asgi_lifespan import LifespanManager
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bootstrap import build_providers
from app.config import Settings
from app.core.providers import Providers
from app.core.security import Cipher
from app.main import create_app
from app.providers.llm.glm import GlmProvider

_HTTP = httpx.AsyncClient()


def _NO_USER() -> None:
    return None


def test_build_providers_registers_the_three_real_providers(
    settings: Settings, db_session_factory: async_sessionmaker[AsyncSession]
) -> None:
    cipher = Cipher(Fernet.generate_key())
    built = build_providers(settings, db_session_factory, cipher, _HTTP, _NO_USER)
    assert isinstance(built, Providers) and built.cipher is cipher
    assert set(built.llm) == {"anthropic", "openai", "glm"} and "fake" not in built.llm


def test_env_keys_come_from_settings(
    settings: Settings, db_session_factory: async_sessionmaker[AsyncSession]
) -> None:
    configured = settings.model_copy(
        update={"anthropic_api_key": "a-key-0001", "zai_api_key": "z-key-0002"}
    )
    built = build_providers(
        configured, db_session_factory, Cipher(Fernet.generate_key()), _HTTP, _NO_USER
    )
    assert dict(built.env_keys) == {"anthropic": "a-key-0001", "openai": None, "glm": "z-key-0002"}


def test_glm_honors_overridden_zai_base_url(
    settings: Settings, db_session_factory: async_sessionmaker[AsyncSession]
) -> None:
    configured = settings.model_copy(update={"zai_base_url": "https://zai.example/v9/"})
    glm = build_providers(
        configured, db_session_factory, Cipher(Fernet.generate_key()), _HTTP, _NO_USER
    ).llm["glm"]
    assert isinstance(glm, GlmProvider)
    assert glm._url("models") == "https://zai.example/v9/models"


async def test_lifespan_stores_providers_and_serves_real_registry(
    settings: Settings, db_engine: object
) -> None:
    app = create_app(settings)
    async with LifespanManager(app):
        assert isinstance(app.state.providers, Providers)
        assert app.state.providers.cipher is app.state.cipher
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get("/api/v1/settings/api-keys")
    assert [e["provider"] for e in r.json()] == ["anthropic", "openai", "glm"]
    assert all(e["source"] is None for e in r.json())
