import httpx
import pytest
from asgi_lifespan import LifespanManager
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.agents.runtime.bus import EventBus
from app.agents.runtime.runner import SessionRunner
from app.config import Settings
from app.core.security import Cipher, KnownSecrets
from app.db.models.accounts import User
from app.features.auth.service import AuthService
from app.main import create_app


async def test_lifespan_creates_secret_and_cipher(settings: Settings, db_engine: object) -> None:
    app = create_app(settings)
    async with LifespanManager(app):
        assert settings.secret_path.exists()
        cipher = app.state.cipher
        assert isinstance(cipher, Cipher)
        assert cipher.decrypt(cipher.encrypt("sk-ant-demo-123456")) == "sk-ant-demo-123456"


async def test_lifespan_registers_env_keys_as_known_secrets(
    settings: Settings, db_engine: object
) -> None:
    configured = settings.model_copy(update={"brave_api_key": "brave-cle-de-test-0001"})
    async with LifespanManager(create_app(configured)):
        assert "brave-cle-de-test-0001" in KnownSecrets.values()


async def test_lifespan_restart_keeps_local_user_and_secret(
    settings: Settings, db_session: AsyncSession
) -> None:
    first_app = create_app(settings)
    async with LifespanManager(first_app):
        first_id = first_app.state.local_user_id
        first_token = first_app.state.cipher.encrypt("valeur")
    second_app = create_app(settings)
    async with LifespanManager(second_app):
        assert second_app.state.local_user_id == first_id
        assert second_app.state.cipher.decrypt(first_token) == "valeur"
    count = await db_session.scalar(select(func.count()).select_from(User))
    assert count == 1


async def test_missing_table_gives_alembic_hint(settings: Settings) -> None:
    # Aucune fixture de schéma : la table `users` n'existe pas.
    with pytest.raises(RuntimeError, match="alembic upgrade head"):
        async with LifespanManager(create_app(settings)):
            pass


async def test_other_operational_error_is_not_relabeled(
    settings: Settings, db_engine: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    error = OperationalError("SELECT 1", {}, Exception("database is locked"))

    async def locked(self: AuthService) -> None:
        raise error

    monkeypatch.setattr(AuthService, "ensure_local_user", locked)
    with pytest.raises(OperationalError) as caught:
        async with LifespanManager(create_app(settings)):
            pass
    assert caught.value is error


async def test_http_client_is_closed_when_composition_fails(
    settings: Settings, db_engine: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    created: list[httpx.AsyncClient] = []
    original = httpx.AsyncClient

    def tracking(*args: object, **kwargs: object) -> httpx.AsyncClient:
        client = original(*args, **kwargs)  # type: ignore[arg-type]
        created.append(client)
        return client

    def boom(*args: object, **kwargs: object) -> None:
        raise ValueError("composition cassée")

    monkeypatch.setattr("app.main.httpx.AsyncClient", tracking)
    monkeypatch.setattr("app.main.build_providers", boom)
    with pytest.raises(ValueError, match="composition cassée"):
        async with LifespanManager(create_app(settings)):
            pass
    assert len(created) == 1 and created[0].is_closed


async def test_shutdown_stops_runner_then_bus_then_engine(
    settings: Settings, db_engine: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    order: list[str] = []
    original_dispose = AsyncEngine.dispose
    original_shutdown = SessionRunner.shutdown

    async def runner_shutdown(self: SessionRunner) -> None:
        order.append("runner")
        await original_shutdown(self)

    async def bus_aclose(self: EventBus) -> None:
        order.append("bus")

    async def dispose(self: AsyncEngine, close: bool = True) -> None:
        order.append("engine")
        await original_dispose(self, close)

    monkeypatch.setattr(SessionRunner, "shutdown", runner_shutdown)
    monkeypatch.setattr(EventBus, "aclose", bus_aclose)
    monkeypatch.setattr(AsyncEngine, "dispose", dispose)
    app = create_app(settings)
    async with LifespanManager(app):
        assert isinstance(app.state.runtime.bus, EventBus)
    assert order == ["runner", "bus", "engine"]
