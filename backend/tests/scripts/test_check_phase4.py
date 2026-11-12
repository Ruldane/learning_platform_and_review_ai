"""Script de contrôle de fin de phase 4 : joué contre l'application réelle (lifespan, moteur,
features), avec les fournisseurs factices et les modèles scriptés du parcours de bout en bout.
Aucun réseau ni LLM réel : la santé est remplacée par une réponse OK, les événements sont lus en
base (le client ASGI de httpx ne parle pas WebSocket)."""

from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine

import scripts.check_phase4 as check
from app.agents.runtime.bus_state import to_event
from app.agents.runtime.repositories import EventRepository
from app.config import Settings
from scripts.check_phase4 import STEPS, CheckFailed, run_check
from scripts.phase4_steps import Run, check_lessons
from tests.e2e.server import build_app


@pytest.fixture
def app(settings: Settings, db_engine: AsyncEngine) -> FastAPI:
    """Serveur de bout en bout : santé remplacée par une réponse OK, modèles scriptés."""
    return build_app(settings)


def _db_feed(app: FastAPI) -> check.EventFeed:
    async def events(session_id: str) -> list[dict[str, Any]]:
        async with app.state.session_factory() as db:
            rows = await EventRepository(db, app.state.local_user_id).list_after(session_id, 0)
        return [to_event(row).model_dump(mode="json") for row in rows]

    return events


@pytest.mark.timeout(600)
async def test_check_runs_against_the_app(app: FastAPI, client: httpx.AsyncClient) -> None:
    steps = await run_check(client, timeout_s=300, events=_db_feed(app))

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


async def test_lessons_wait_for_their_pdf() -> None:
    """Une leçon passe « prête » avant que son PDF soit rendu : le contrôle attend le PDF."""
    polls = {"count": 0}

    def api(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/lessons"):
            polls["count"] += 1
            ready = polls["count"] > 2
            lesson = {"id": "l1", "week_rank": 1, "status": "ready", "pdf_available": ready}
            return httpx.Response(200, json=[lesson])
        if path.endswith("/pdf"):
            if polls["count"] <= 2:
                return httpx.Response(404, json={"error": {"code": "lesson_pdf_missing"}})
            return httpx.Response(200, content=b"%PDF-1.4")
        resources = [{"id": f"r{n}"} for n in range(4)]
        return httpx.Response(200, json={"id": "l1", "resources": resources})

    async def no_events(session_id: str) -> list[dict[str, Any]]:
        return []

    transport = httpx.MockTransport(api)
    async with httpx.AsyncClient(transport=transport, base_url="http://api") as client:
        run = Run(client, no_events, timeout_s=5, program_id="p1", week_ranks=[1])
        await check_lessons(run)

    assert polls["count"] == 3
