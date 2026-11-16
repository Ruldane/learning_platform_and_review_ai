"""Fixtures des tests du radar : l'app réelle (lanceur factice, horloge figée au lundi 16 novembre
2026, 9 h à Paris) pour les routes, et un `Radar` autonome sur la base de test pour le port, la
fin d'un relevé et la tâche du lundi."""

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi import FastAPI

from app.core.security import Cipher
from app.features.radar.service.runtime import RadarRuntime
from app.features.radar.service.store import AgentRadarStore
from app.features.research.service.runtime import ResearchRuntime
from app.features.settings.keys_service import DbKeyReader
from tests.features.lessons.conftest import RecordingLauncher
from tests.features.program.support import Factory
from tests.features.radar.support import ME, NOW, OTHER, Radar, add_users
from tests.support.memory import FakeWebReader
from tests.support.research import fake_research_providers


@pytest.fixture
async def client(client: httpx.AsyncClient, app: FastAPI) -> httpx.AsyncClient:
    """Le client de la suite ; le radar de l'app a l'horloge figée."""
    app.state.daily.radar.now = lambda: NOW
    return client


@pytest.fixture
def launcher_spy(client: httpx.AsyncClient, app: FastAPI) -> RecordingLauncher:
    """Remplace le lanceur du radar, une fois l'app démarrée (`client`)."""
    spy = RecordingLauncher(app.state.session_factory)
    app.state.daily.radar.launcher = spy
    return spy


@pytest.fixture
def launcher(db_session_factory: Factory) -> RecordingLauncher:
    return RecordingLauncher(db_session_factory)


@pytest.fixture
async def radar(db_session_factory: Factory, launcher: RecordingLauncher) -> Radar:
    await add_users(db_session_factory, ME, OTHER)
    web = FakeWebReader()
    keys = DbKeyReader(db_session_factory, Cipher(Fernet.generate_key()), {})
    research = ResearchRuntime(db_session_factory, fake_research_providers(web), keys)
    rt = RadarRuntime(db_session_factory, launcher, research, now=lambda: NOW)
    return Radar(rt, AgentRadarStore(rt), web, db_session_factory)
