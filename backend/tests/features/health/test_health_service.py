import asyncio
import logging

import httpx
import pytest

from app.features.health.service import HealthService
from app.providers.health import HealthCheck, HealthStatus
from tests.features.health.conftest import FakeCheck, RaisingCheck


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


class _SlowWithOwnCap(_Slow):
    def __init__(self, name: str, seconds: float, timeout: float) -> None:
        super().__init__(name, seconds)
        self.timeout = timeout


async def test_all_ok() -> None:
    assert (await HealthService([ok("db"), ok("qdrant")]).run()).status == "ok"


async def test_service_down_is_degraded() -> None:
    assert (await HealthService([ok("db"), ko("qdrant")]).run()).status == "degraded"


async def test_db_down_is_down() -> None:
    assert (await HealthService([ko("db"), ok("qdrant")]).run()).status == "down"


async def test_slow_or_raising_check_is_reported() -> None:
    checks = [ok("db"), _Slow("searxng", 5), RaisingCheck("gotenberg", RuntimeError("secret"))]
    r = await HealthService(checks, timeout=0.05).run()
    assert r.checks["searxng"].detail == "Délai dépassé" and not r.checks["searxng"].ok
    assert r.checks["gotenberg"].ok is False and r.status == "degraded"


async def test_check_may_ask_for_a_longer_cap_than_the_default() -> None:
    patient = _SlowWithOwnCap("searxng", 0.2, timeout=2.0)
    r = await HealthService([ok("db"), patient], timeout=0.05).run()
    assert r.checks["searxng"].ok
    impatient = _SlowWithOwnCap("searxng", 5, timeout=0.05)
    r = await HealthService([ok("db"), impatient], timeout=0.01).run()
    assert r.checks["searxng"].detail == "Délai dépassé"


async def test_exception_detail_is_only_the_type_name() -> None:
    boom = RaisingCheck("qdrant", httpx.ConnectError("http://secret-host sk-secret-key"))
    r = await HealthService([ok("db"), boom]).run()
    assert r.checks["qdrant"].detail == "Erreur : ConnectError"


async def test_failed_check_is_logged_with_type_name_only(
    caplog: pytest.LogCaptureFixture,
) -> None:
    boom = RaisingCheck("qdrant", httpx.ConnectError("http://secret-host sk-secret-key"))
    with caplog.at_level(logging.WARNING, logger="app.features.health.service"):
        await HealthService([ok("db"), boom, _Slow("searxng", 5)], timeout=0.05).run()
    messages = [r.getMessage() for r in caplog.records]
    assert "health check qdrant failed: ConnectError" in messages
    assert "health check searxng failed: TimeoutError" in messages
    assert "secret" not in caplog.text


async def test_httpx_timeout_is_reported_as_timeout() -> None:
    r = await HealthService([ok("db"), RaisingCheck("qdrant", httpx.ReadTimeout("x"))]).run()
    assert r.checks["qdrant"].detail == "Délai dépassé"


async def test_checks_run_in_parallel() -> None:
    checks = [_Slow(f"c{i}", 0.2) for i in range(5)] + [ok("db")]
    loop = asyncio.get_running_loop()
    start = loop.time()
    await HealthService(checks).run()
    assert loop.time() - start < 0.6
