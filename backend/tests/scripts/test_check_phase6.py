"""Contrôle de la phase 6, partie « capture », joué de bout en bout contre l'application réelle
(lifespan, moteur, features, extracteur de mise en page réel mais local) : l'Archiviste, le
Maquettiste et l'Analyste scriptés (`capture_scripts`), les fournisseurs factices. Aucun réseau
ni LLM réel ; la santé est remplacée par une réponse OK. Les journaux de l'application, relus par
la dernière étape, viennent de la capture des journaux du test."""

import logging

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine

import scripts.check_phase6 as check
from app.config import Settings
from app.core.providers import MemoryProviders, PublishingProviders, ResearchProviders
from app.features.health.router import get_health_service
from app.main import create_app
from scripts.check_phase6 import CAPTURE_STEPS, CheckFailed, run_check
from tests.e2e.scripted_models import ScriptedModels
from tests.e2e.server import healthy_service
from tests.scripts.phase6_support import capture_scripts
from tests.support.memory import fake_publishing_providers
from tests.support.text_renderer import TextHtmlRenderer


@pytest.fixture
def models() -> ScriptedModels:
    return ScriptedModels(capture_scripts())


@pytest.fixture
def publishing_providers() -> PublishingProviders:
    """Un rendu lisible : le PDF du gabarit se relit avec l'extracteur réel (ressemblance)."""
    return fake_publishing_providers(TextHtmlRenderer())  # type: ignore[arg-type]


@pytest.fixture
def app(
    settings: Settings,
    db_engine: AsyncEngine,
    memory_providers: MemoryProviders,
    research_providers: ResearchProviders,
    publishing_providers: PublishingProviders,
    models: ScriptedModels,
) -> FastAPI:
    """L'application sur les modèles scriptés de la capture, la santé sans sonde."""
    built = create_app(
        settings,
        memory_providers=memory_providers,
        research_providers=research_providers,
        publishing_providers=publishing_providers,
        chat_models=models,
    )
    built.dependency_overrides[get_health_service] = healthy_service
    return built


@pytest.mark.timeout(300)
async def test_check_phase6_capture_on_test_app(
    client: httpx.AsyncClient, models: ScriptedModels, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)

    steps = await run_check(client, part="capture", timeout_s=240, logs=caplog.text)

    assert steps == list(CAPTURE_STEPS)
    assert len(steps) == 6
    assert models.served["archivist"] > 0 and models.served["designer"] > 0
    assert models.served["analyst"] == 2  # l'analyse, puis les rattachements


@pytest.mark.timeout(300)
async def test_second_run_rereads_instead_of_redoing(
    client: httpx.AsyncClient, models: ScriptedModels
) -> None:
    await run_check(client, part="capture", timeout_s=240, logs="")
    served = dict(models.served)

    again = await run_check(client, part="capture", timeout_s=240, logs="")

    assert again == list(CAPTURE_STEPS)
    assert models.served["archivist"] == served["archivist"]  # profil validé : relu
    assert models.served["designer"] == served["designer"]  # modèle prêt : relu
    assert models.served["analyst"] == served["analyst"]  # même offre : 200, rien de refait


async def test_logs_step_fails_without_logs_or_with_personal_data(
    client: httpx.AsyncClient,
) -> None:
    with pytest.raises(CheckFailed) as missing:
        await run_check(client, part="capture", timeout_s=240, logs=None)
    assert missing.value.step == "journaux"

    with pytest.raises(CheckFailed) as leaked:
        await run_check(client, part="capture", timeout_s=240, logs="Camille Exemple a postulé")
    assert leaked.value.step == "journaux"
    assert "Camille" not in str(leaked.value)  # le message ne recopie pas ce qui a fuité


async def test_part_not_written_yet_is_refused(client: httpx.AsyncClient) -> None:
    with pytest.raises(CheckFailed) as refused:
        await run_check(client, part="revue", timeout_s=10)
    assert refused.value.step == "partie"


def test_main_exposes_the_parts() -> None:
    assert callable(check.main)
