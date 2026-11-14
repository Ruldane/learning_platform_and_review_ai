"""Contrôle de la phase 6, parties « revue » et « tout », joué de bout en bout contre l'application
réelle (lifespan, moteur, features) : les six agents du CV scriptés (`cv_scripts`, D135), le web
factice de la fiche entreprise, le rendu PDF textuel (relisible par pdfplumber). Aucun réseau ni
LLM réel ; la santé est remplacée par une réponse OK."""

import logging

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine

from app.config import Settings
from app.core.providers import MemoryProviders, PublishingProviders
from app.features.health.router import get_health_service
from app.main import create_app
from app.providers.search.fake import FakeSearch
from scripts.check_phase6 import CAPTURE_STEPS, REVIEW_STEPS, CheckFailed, run_check
from tests.e2e.cv_script import cv_scripts, script_company_web
from tests.e2e.scripted_models import ScriptedModels
from tests.e2e.server import healthy_service
from tests.support.memory import FakeWebReader, fake_publishing_providers
from tests.support.research import fake_research_providers
from tests.support.text_renderer import TextHtmlRenderer


@pytest.fixture
def models() -> ScriptedModels:
    return ScriptedModels(cv_scripts())


@pytest.fixture
def publishing_providers() -> PublishingProviders:
    return fake_publishing_providers(TextHtmlRenderer())  # type: ignore[arg-type]


@pytest.fixture
def app(
    settings: Settings,
    db_engine: AsyncEngine,
    memory_providers: MemoryProviders,
    publishing_providers: PublishingProviders,
    models: ScriptedModels,
) -> FastAPI:
    """L'application sur les modèles scriptés du CV et la fiche d'une entreprise fictive."""
    assert isinstance(memory_providers.web, FakeWebReader)
    search = FakeSearch("searxng")
    script_company_web(memory_providers.web, search)
    built = create_app(
        settings,
        memory_providers=memory_providers,
        research_providers=fake_research_providers(memory_providers.web, searxng=search),
        publishing_providers=publishing_providers,
        chat_models=models,
    )
    built.dependency_overrides[get_health_service] = healthy_service
    return built


@pytest.mark.timeout(300)
async def test_check_phase6_tout_on_test_app(
    client: httpx.AsyncClient, models: ScriptedModels, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)

    steps = await run_check(client, part="tout", timeout_s=240, logs=caplog.text)

    assert steps == [*CAPTURE_STEPS, *REVIEW_STEPS]
    assert len(steps) == 12
    assert models.served["ats_reader"] > 0 and models.served["recruiter"] > 0


@pytest.mark.timeout(300)
async def test_second_run_reuses_what_exists_and_reviews_again(
    client: httpx.AsyncClient, models: ScriptedModels
) -> None:
    first = await run_check(client, part="tout", timeout_s=240, logs="")
    served = dict(models.served)

    again = await run_check(client, part="revue", timeout_s=240, logs="")

    assert len(first) == 12
    assert again == [*CAPTURE_STEPS[:3], *REVIEW_STEPS]
    assert models.served["archivist"] == served["archivist"]  # profil validé : relu
    assert models.served["designer"] == served["designer"]  # modèle prêt : relu
    assert models.served["analyst"] == served["analyst"]  # même offre : 200, rien de refait
    assert models.served["ats_reader"] > served["ats_reader"]  # la revue close : une nouvelle


async def test_review_logs_step_fails_without_logs(client: httpx.AsyncClient) -> None:
    with pytest.raises(CheckFailed) as missing:
        await run_check(client, part="revue", timeout_s=240, logs=None)
    assert missing.value.step == "journaux"
