"""Fixtures des tests de l'IDE (10.A2) : l'application réelle, une utilisatrice (`act_as`) et un bac
à sable factice (`FakeSandbox`, jamais le vrai) que le test pose sur `app.state.providers`."""

from collections.abc import Callable

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine

from app.config import Settings
from app.core.providers import MemoryProviders, PublishingProviders, ResearchProviders
from app.main import create_app
from app.providers.sandbox.fake import FakeSandbox, Script
from tests.features.ide.support import USER
from tests.features.ide.teach_support import ScriptedModels
from tests.sessions_support import act_as

OTHER = "utilisatrice-b"

__all__ = ["OTHER", "USER"]
UseSandbox = Callable[[dict[str, Script]], FakeSandbox]


@pytest.fixture
def me(app: FastAPI, client: httpx.AsyncClient) -> str:
    """Les requêtes sont celles de `USER`."""
    act_as(app, USER)
    return USER


@pytest.fixture
def use_sandbox(app: FastAPI, client: httpx.AsyncClient) -> UseSandbox:
    """`use_sandbox({"*": "sortie"})` : pose un bac factice scripté (clé `"*"` : tout travail)."""

    def use(scripted: dict[str, Script]) -> FakeSandbox:
        fake = FakeSandbox(scripted)
        app.state.providers.sandbox = fake
        return fake

    return use


@pytest.fixture
def models() -> ScriptedModels:
    """Les faux modèles du professeur et du rédacteur d'exercices (aucun appel réel)."""
    return ScriptedModels()


@pytest.fixture
def app(
    settings: Settings,
    db_engine: AsyncEngine,
    memory_providers: MemoryProviders,
    research_providers: ResearchProviders,
    publishing_providers: PublishingProviders,
    models: ScriptedModels,
) -> FastAPI:
    """L'application réelle (moteur d'agents, port de l'IDE) sur les faux modèles."""
    return create_app(
        settings,
        memory_providers=memory_providers,
        research_providers=research_providers,
        publishing_providers=publishing_providers,
        chat_models=models,
    )
