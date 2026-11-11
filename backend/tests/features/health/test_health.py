import asyncio
import logging
from collections.abc import Callable

import httpx
import pytest
import respx
from asgi_lifespan import LifespanManager
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.core.security import Cipher
from app.features.health.checks import DatabaseCheck, LlmKeysCheck
from app.features.health.service import HealthService
from app.features.settings.keys_service import ApiKeyService
from app.main import create_app
from app.providers.health import HealthCheck, HealthStatus
from app.providers.llm.fake import FakeLlmProvider
from tests.features.health.conftest import FakeCheck, override_health_checks

HEALTH = "/api/v1/health"
Override = Callable[[list[HealthCheck]], None]


def ok(name: str) -> HealthCheck:
    return FakeCheck(name, HealthStatus(ok=True, detail="Disponible"))


def ko(name: str) -> HealthCheck:
    return FakeCheck(name, HealthStatus(ok=False, detail="Indisponible"))


class _Slow:
    def __init__(self, name: str, seconds: float) -> None:
        self.name = name
        self._seconds = seconds

    async def check(self) -> HealthStatus:
        await asyncio.sleep(self._seconds)
        return HealthStatus(ok=True, detail="Disponible")


class _Raising:
    def __init__(self, name: str, error: Exception) -> None:
        self.name = name
        self._error = error

    async def check(self) -> HealthStatus:
        raise self._error


async def test_all_ok() -> None:
    assert (await HealthService([ok("db"), ok("qdrant")]).run()).status == "ok"


async def test_service_down_is_degraded() -> None:
    assert (await HealthService([ok("db"), ko("qdrant")]).run()).status == "degraded"


async def test_db_down_is_down() -> None:
    assert (await HealthService([ko("db"), ok("qdrant")]).run()).status == "down"


async def test_slow_or_raising_check_is_reported() -> None:
    checks = [ok("db"), _Slow("searxng", 5), _Raising("gotenberg", RuntimeError("secret"))]
    r = await HealthService(checks, timeout=0.05).run()
    assert r.checks["searxng"].detail == "Délai dépassé" and not r.checks["searxng"].ok
    assert r.checks["gotenberg"].ok is False and r.status == "degraded"


async def test_exception_detail_is_only_the_type_name() -> None:
    boom = _Raising("qdrant", httpx.ConnectError("http://secret-host sk-secret-key"))
    r = await HealthService([ok("db"), boom]).run()
    assert r.checks["qdrant"].detail == "Erreur : ConnectError"


async def test_failed_check_is_logged_with_type_name_only(
    caplog: pytest.LogCaptureFixture,
) -> None:
    boom = _Raising("qdrant", httpx.ConnectError("http://secret-host sk-secret-key"))
    with caplog.at_level(logging.WARNING, logger="app.features.health.service"):
        await HealthService([ok("db"), boom, _Slow("searxng", 5)], timeout=0.05).run()
    messages = [r.getMessage() for r in caplog.records]
    assert "health check qdrant failed: ConnectError" in messages
    assert "health check searxng failed: TimeoutError" in messages
    assert "secret" not in caplog.text


async def test_httpx_timeout_is_reported_as_timeout() -> None:
    r = await HealthService([ok("db"), _Raising("qdrant", httpx.ReadTimeout("x"))]).run()
    assert r.checks["qdrant"].detail == "Délai dépassé"


async def test_checks_run_in_parallel() -> None:
    checks = [_Slow(f"c{i}", 0.2) for i in range(5)] + [ok("db")]
    loop = asyncio.get_running_loop()
    start = loop.time()
    await HealthService(checks).run()
    assert loop.time() - start < 0.6


async def test_database_check_ok(db_session_factory: async_sessionmaker[AsyncSession]) -> None:
    check = DatabaseCheck(db_session_factory)
    assert (await check.check()).ok and check.name == "db"


async def test_database_failure_makes_the_report_down() -> None:
    def broken() -> AsyncSession:
        raise OSError("disque absent")

    r = await HealthService([DatabaseCheck(broken)]).run()  # type: ignore[arg-type]
    assert r.status == "down" and r.checks["db"].detail == "Erreur : OSError"


# --- clés LLM ---------------------------------------------------------------------------------

USER = "u1"
Factory = async_sessionmaker[AsyncSession]


class _Named(FakeLlmProvider):
    def __init__(self, name: str, label: str) -> None:
        super().__init__([])
        self.name = name
        self.label = label


@pytest.fixture
def cipher() -> Cipher:
    return Cipher(Fernet.generate_key())


@pytest.fixture
def llm() -> dict[str, FakeLlmProvider]:
    return {"anthropic": _Named("anthropic", "Anthropic"), "openai": _Named("openai", "OpenAI")}


def make_check(
    factory: Factory,
    cipher: Cipher,
    llm: dict[str, FakeLlmProvider],
    env_keys: dict[str, str | None],
    user_id: str | None = USER,
) -> LlmKeysCheck:
    return LlmKeysCheck(factory, cipher, env_keys, llm, lambda: user_id)


async def store_key(
    session: AsyncSession, cipher: Cipher, llm: dict[str, FakeLlmProvider], user: str = USER
) -> None:
    await ApiKeyService(session, user, cipher, {}, llm).set("openai", "sk-secret-0123456789")
    await session.commit()


async def test_llm_check_without_any_key(
    db_session_factory: Factory, cipher: Cipher, llm: dict[str, FakeLlmProvider]
) -> None:
    check = make_check(db_session_factory, cipher, llm, {})
    status = await check.check()
    assert not status.ok and check.name == "llm"
    assert status.detail == "Anthropic : aucune clé ; OpenAI : aucune clé"


async def test_llm_check_with_ui_key(
    db_session_factory: Factory,
    db_session: AsyncSession,
    cipher: Cipher,
    llm: dict[str, FakeLlmProvider],
) -> None:
    await store_key(db_session, cipher, llm)
    status = await make_check(db_session_factory, cipher, llm, {}).check()
    assert status.ok
    assert status.detail == "Anthropic : aucune clé ; OpenAI : clé présente"
    assert "0123456789" not in status.detail


async def test_llm_check_with_env_key(
    db_session_factory: Factory, cipher: Cipher, llm: dict[str, FakeLlmProvider]
) -> None:
    check = make_check(db_session_factory, cipher, llm, {"anthropic": "env-key-0001"})
    status = await check.check()
    assert status.ok and "Anthropic : clé présente" in status.detail


async def test_llm_check_unreadable_key_does_not_count(
    db_session_factory: Factory,
    db_session: AsyncSession,
    cipher: Cipher,
    llm: dict[str, FakeLlmProvider],
) -> None:
    await store_key(db_session, cipher, llm)
    other = Cipher(Fernet.generate_key())
    status = await make_check(db_session_factory, other, llm, {}).check()
    assert not status.ok and "OpenAI : clé illisible" in status.detail


async def test_llm_check_scopes_keys_to_the_user(
    db_session_factory: Factory,
    db_session: AsyncSession,
    cipher: Cipher,
    llm: dict[str, FakeLlmProvider],
) -> None:
    await store_key(db_session, cipher, llm, user="autre")
    assert not (await make_check(db_session_factory, cipher, llm, {}).check()).ok


async def test_llm_check_without_user(
    db_session_factory: Factory, cipher: Cipher, llm: dict[str, FakeLlmProvider]
) -> None:
    status = await make_check(db_session_factory, cipher, llm, {}, user_id=None).check()
    assert not status.ok and status.detail == "Aucun utilisateur local."


# --- route ------------------------------------------------------------------------------------


async def test_health_route_shape(client: httpx.AsyncClient, override_checks: Override) -> None:
    override_checks([ok("db"), ko("qdrant")])
    response = await client.get(HEALTH)
    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "degraded" and "db" in body["checks"]
    assert body["checks"]["qdrant"] == {"ok": False, "detail": "Indisponible"}


async def test_health_route_is_200_even_when_down(
    client: httpx.AsyncClient, override_checks: Override
) -> None:
    override_checks([ko("db")])
    response = await client.get(HEALTH)
    assert response.status_code == 200 and response.json()["status"] == "down"


async def test_health_route_never_leaks_exception_messages(
    client: httpx.AsyncClient, override_checks: Override
) -> None:
    override_checks([ok("db"), _Raising("qdrant", RuntimeError("clé sk-ant-0000 http://x"))])
    text = (await client.get(HEALTH)).text
    assert "sk-ant" not in text and "Erreur : RuntimeError" in text


async def test_health_route_needs_no_session_in_google_mode(
    settings: Settings, db_engine: object
) -> None:
    # Mode `google` sans connexion : les routes protégées répondent 401, pas la santé.
    app = create_app(settings.model_copy(update={"auth_mode": "google"}))
    async with LifespanManager(app):
        override_health_checks(app, [ok("db")])
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(HEALTH)
    assert response.status_code == 200 and response.json()["status"] == "ok"


# --- câblage réel (bootstrap + lifespan) -------------------------------------------------------


async def test_real_wiring_reports_the_six_checks(settings: Settings, db_engine: object) -> None:
    configured = settings.model_copy(update={"anthropic_api_key": "env-key-for-health-0001"})
    app = create_app(configured)
    with respx.mock(assert_all_called=True) as mock:
        tags = {"models": [{"name": "bge-m3:latest"}]}
        mock.get("http://qdrant:6333/readyz").respond(200)
        mock.get("http://ollama:11434/api/tags").respond(json=tags)
        mock.get("http://searxng:8080/healthz").respond(200)
        mock.get(url__startswith="http://searxng:8080/search").respond(json={"results": []})
        mock.get("http://gotenberg:3000/health").respond(200)
        async with LifespanManager(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                body = (await client.get(HEALTH)).json()
    assert set(body["checks"]) == {"db", "qdrant", "ollama", "searxng", "gotenberg", "llm"}
    assert body["status"] == "ok", body
    assert "env-key-for-health-0001" not in str(body)


async def test_real_wiring_unreachable_services_are_degraded(
    settings: Settings, db_engine: object
) -> None:
    app = create_app(settings)
    with respx.mock as mock:
        for host in ("qdrant", "ollama", "searxng", "gotenberg"):
            mock.route(host=host).mock(side_effect=httpx.ConnectError("hôte secret"))
        async with LifespanManager(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                body = (await client.get(HEALTH)).json()
    assert body["status"] == "degraded"
    assert body["checks"]["qdrant"]["detail"] == "Erreur : ConnectError"
    assert body["checks"]["db"]["ok"] is True
