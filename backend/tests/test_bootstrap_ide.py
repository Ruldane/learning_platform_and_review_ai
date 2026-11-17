"""La composition de l'IDE (10.A1) : le bac à sable et son contrôle de santé."""

import httpx
from fastapi import FastAPI

from app.features.health.checks import SandboxCheck
from app.providers.sandbox.spool import SpoolSandbox


async def test_compose_ide_puts_a_spool_sandbox_and_its_check(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    providers = app.state.providers
    assert isinstance(providers.sandbox, SpoolSandbox)
    assert any(isinstance(check, SandboxCheck) for check in providers.health_checks)
    assert app.state.settings.sandbox_spool_dir.as_posix() == "/spool"
