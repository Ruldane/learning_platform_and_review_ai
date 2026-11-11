"""Outils des tests de la feature `sessions` et du WebSocket : l'app réelle (lifespan, runner,
bus, checkpointer) avec les parcours de test et le faux fournisseur LLM. Aucun appel réseau."""

import asyncio
import time
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.main as main_module
from app.agents.graphs.registry import GRAPHS
from app.core.deps import CurrentUser, get_current_user
from tests.agents.graphs_for_tests import TEST_GRAPHS, Probe, reset_probe
from tests.agents.runtime.runner_helpers import fake_llm

TIMEOUT = 5.0
API = "/api/v1/sessions"


def use_test_runtime(monkeypatch: pytest.MonkeyPatch) -> Probe:
    """Parcours de test dans le registre global et faux LLM pour le runtime du lifespan."""
    for name, spec in TEST_GRAPHS.items():
        monkeypatch.setitem(GRAPHS, name, spec)
    real = main_module.agent_runtime

    def fake_runtime(settings: Any, factory: Any, models: Any, prices: Any, run: Any) -> Any:
        return real(settings, factory, fake_llm(["Bonjour à toi"] * 50), prices, run)

    monkeypatch.setattr(main_module, "agent_runtime", fake_runtime)
    return reset_probe()


def act_as(app: FastAPI, user_id: str) -> None:
    """Les requêtes suivantes sont celles de `user_id` (isolation entre utilisateurs)."""
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(id=user_id, email=None)


def _settled(app: Any, sid: str) -> bool:
    """Tâche de la session finie. Lu AVANT la lecture du statut : le runner écrit le statut
    avant de publier l'événement qui va avec (`interrupt.requested`, `run.completed`, D46) ;
    une tâche déjà finie a tout écrit, donc la lecture qui suit voit tout."""
    return not app.state.runtime.runner.is_active(sid)


async def wait_status(client: httpx.AsyncClient, sid: str, status: str) -> dict[str, Any]:
    app = client._transport.app  # type: ignore[attr-defined]  # ASGITransport des fixtures
    async with asyncio.timeout(TIMEOUT):
        while True:
            settled = status == "running" or _settled(app, sid)
            view: dict[str, Any] = (await client.get(f"{API}/{sid}")).json()
            if settled and view["status"] == status:
                return view
            await asyncio.sleep(0.01)


def wait_status_sync(client: TestClient, sid: str, status: str) -> dict[str, Any]:
    deadline = time.monotonic() + TIMEOUT
    while True:
        settled = status == "running" or _settled(client.app, sid)
        view: dict[str, Any] = client.get(f"{API}/{sid}").json()
        if settled and view["status"] == status:
            return view
        assert time.monotonic() < deadline, f"statut {view['status']} au lieu de {status}"
        time.sleep(0.01)


def wait_until_sync(predicate: Any) -> None:
    deadline = time.monotonic() + TIMEOUT
    while not predicate():
        assert time.monotonic() < deadline, "condition jamais remplie"
        time.sleep(0.01)
