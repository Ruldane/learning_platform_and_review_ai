"""Script de contrôle de fin de phase 4 : joué de bout en bout contre l'application réelle
(lifespan, moteur, features) servie par uvicorn sur 127.0.0.1, avec les fournisseurs factices et
les modèles scriptés du parcours de bout en bout. Les événements passent par le vrai WebSocket.
Aucun réseau externe ni LLM réel : la santé est remplacée par une réponse OK."""

from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine

import scripts.check_phase4 as check
from app.config import Settings
from scripts.check_phase4 import STEPS, CheckFailed, run_check
from tests.e2e.server import build_app
from tests.scripts.live_server import serving


@pytest.fixture
def app(settings: Settings, db_engine: AsyncEngine) -> FastAPI:
    """Serveur de bout en bout : santé remplacée par une réponse OK, modèles scriptés."""
    return build_app(settings)


@pytest.mark.timeout(600)
async def test_check_runs_against_the_app(app: FastAPI) -> None:
    async with serving(app) as base, httpx.AsyncClient(base_url=base, timeout=30) as client:
        steps = await run_check(client, timeout_s=300)  # événements lus par WebSocket

    assert steps == [
        "santé",
        "objectif",
        "cadrage",
        "conseil",
        "choix",
        "programme",
        "validation",
        "leçons",
        "exports",
    ]
    assert steps == list(STEPS)
    assert app.state.injected_chat_models.remaining() == {}  # tout le script a été joué


async def test_check_stops_at_the_first_failed_step() -> None:
    def degraded(request: httpx.Request) -> httpx.Response:
        checks = {"db": {"ok": True}, "gotenberg": {"ok": False, "detail": "Délai dépassé"}}
        return httpx.Response(200, json={"status": "degraded", "checks": checks})

    transport = httpx.MockTransport(degraded)
    async with httpx.AsyncClient(transport=transport, base_url="http://api") as client:
        with pytest.raises(CheckFailed) as caught:
            await run_check(client, timeout_s=5)

    assert caught.value.step == "santé"
    assert "gotenberg" in str(caught.value)


def test_main_exits_with_one_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    async def failing(client: httpx.AsyncClient, **kwargs: Any) -> list[str]:
        raise CheckFailed("santé", "Service indisponible : gotenberg.")

    monkeypatch.setattr(check, "run_check", failing)
    with pytest.raises(SystemExit) as exited:
        check.main(["--api", "http://localhost:1"])
    assert exited.value.code == 1


def test_main_exits_with_zero_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    async def passing(client: httpx.AsyncClient, **kwargs: Any) -> list[str]:
        return list(STEPS)

    monkeypatch.setattr(check, "run_check", passing)
    with pytest.raises(SystemExit) as exited:
        check.main(["--api", "http://localhost:1"])
    assert exited.value.code == 0
