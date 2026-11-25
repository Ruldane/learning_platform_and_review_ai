"""Le contrôle « Bac à sable » (10.A1) : ok si le lanceur bat, sinon dégradé, sans rien exécuter."""

import os
import time
from pathlib import Path

from app.features.health.checks import SandboxCheck
from app.features.health.service import HealthService
from app.providers.health import HealthStatus
from app.providers.sandbox.fake import FakeSandbox
from app.providers.sandbox.spool import SpoolSandbox
from tests.features.health.conftest import FakeCheck


async def test_ok_when_the_runner_beats(tmp_path: Path) -> None:
    (tmp_path / "heartbeat").write_text("x")
    status = await SandboxCheck(SpoolSandbox(tmp_path)).check()
    assert status.ok is True


async def test_degraded_when_the_heartbeat_is_old_or_absent(tmp_path: Path) -> None:
    check = SandboxCheck(SpoolSandbox(tmp_path))
    assert (await check.check()).ok is False
    (tmp_path / "heartbeat").write_text("x")
    old = time.time() - 60
    os.utime(tmp_path / "heartbeat", (old, old))
    status = await check.check()
    assert status.ok is False and "Sandbox" in status.detail


async def test_a_dead_sandbox_degrades_the_report_but_never_downs_it() -> None:
    class Dead(FakeSandbox):
        async def healthy(self) -> bool:
            return False

    ok = FakeCheck("db", HealthStatus(ok=True, detail="Disponible"))
    report = await HealthService([ok, SandboxCheck(Dead())]).run()
    assert report.status == "degraded"
    assert report.checks["sandbox"].ok is False
