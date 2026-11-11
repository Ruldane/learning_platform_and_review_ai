import pytest
from asgi_lifespan import LifespanManager
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

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
