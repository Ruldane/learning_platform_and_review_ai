from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.agents.graphs_for_tests import Probe
from tests.sessions_support import use_test_runtime


@pytest.fixture(autouse=True)
def probe(monkeypatch: pytest.MonkeyPatch) -> Iterator[Probe]:
    """Avant l'app (autouse) : son lifespan construit le runtime avec les parcours de test."""
    probe = use_test_runtime(monkeypatch)
    yield probe
    probe.release_b.set()


@pytest.fixture
def sync_client(app: FastAPI) -> Iterator[TestClient]:
    """Client synchrone (WebSocket) : lifespan, requêtes et WebSocket sur la même boucle."""
    with TestClient(app) as client:
        yield client


@pytest.fixture(autouse=True)
def short_idle(monkeypatch: pytest.MonkeyPatch) -> None:
    """Silence de 50 ms (au lieu d'une seconde) avant de lire le statut d'une session."""
    monkeypatch.setattr("app.realtime.replay.IDLE_CHECK_S", 0.05)
