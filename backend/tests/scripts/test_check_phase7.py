"""Contrôle de la phase 7, joué de bout en bout contre l'application réelle (lifespan, moteur,
features) servie par uvicorn sur 127.0.0.1 : les préalables viennent du contrôle de la phase 6
(partie `tout`, agents du CV scriptés), puis `suivi` et `kit` avec l'Assistant de suivi et
l'Éclaireur scriptés (`phase7_scripts`), le web factice de la fiche d'une entreprise, le rendu PDF
textuel. Les événements passent par le vrai WebSocket. Aucun réseau ni LLM réel ; la santé est
remplacée par une réponse OK."""

import json
import logging
from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine

from app.config import Settings
from app.core.providers import MemoryProviders, PublishingProviders
from app.features.health.router import get_health_service
from app.main import create_app
from app.providers.search.fake import FakeSearch
from scripts.check_phase6 import run_check as run_phase6
from scripts.check_phase7 import KIT_STEPS, SUIVI_STEPS, CheckFailed, run_check
from tests.e2e.cv_script import cv_scripts, script_company_web
from tests.e2e.scripted_models import ScriptedModels, merge_scripts
from tests.e2e.server import healthy_service
from tests.scripts.live_server import serving
from tests.scripts.phase7_support import english_letter, phase7_scripts
from tests.support.memory import FakeWebReader, fake_publishing_providers
from tests.support.research import fake_research_providers
from tests.support.text_renderer import TextHtmlRenderer


@pytest.fixture
def letter_reply() -> str | None:
    """La lettre scriptée (celle par défaut : 300 mots en français) ; les tests la changent."""
    return None


@pytest.fixture
def models(letter_reply: str | None) -> ScriptedModels:
    return ScriptedModels(merge_scripts(cv_scripts(), phase7_scripts(letter_reply=letter_reply)))


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
    """L'application sur les modèles scriptés du CV et des candidatures."""
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


@pytest.fixture
async def api(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    """Un client HTTP sur le serveur réel (le WebSocket des sessions y passe)."""
    async with serving(app) as base, httpx.AsyncClient(base_url=base, timeout=60) as client:
        yield client


@pytest.fixture
async def phase6(api: httpx.AsyncClient) -> None:
    """Les préalables : profil validé, offre fictive analysée, version de CV prête."""
    await run_phase6(api, part="tout", timeout_s=240, logs="")


@pytest.mark.timeout(900)
async def test_suivi_then_kit_on_test_app(
    api: httpx.AsyncClient,
    phase6: None,
    models: ScriptedModels,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    caplog.set_level(logging.INFO)

    suivi = await run_check(api, part="suivi", timeout_s=300, logs=caplog.text)
    kit = await run_check(api, part="kit", timeout_s=300, logs=caplog.text)

    assert suivi == list(SUIVI_STEPS)
    assert kit == list(KIT_STEPS)
    assert len(suivi) == 6 and len(kit) == 3
    assert models.served["tracker"] == 1 + 5 + 1  # la phrase, cinq pièces, le nouvel essai du pitch
    assert models.served["scout"] > 0
    out = capsys.readouterr().out
    assert "[ok] kit" in out and "2 à vérifier" in out and "1 terme(s)" in out
    assert "Kubernetes" not in out  # les termes ne sont jamais affichés


@pytest.mark.timeout(900)
async def test_second_run_is_repeatable(api: httpx.AsyncClient, phase6: None) -> None:
    first = await run_check(api, part="suivi", timeout_s=300, logs="")
    again = await run_check(api, part="suivi", timeout_s=300, logs="")
    kit = await run_check(api, part="kit", timeout_s=300, logs="")
    kit_again = await run_check(api, part="kit", timeout_s=300, logs="")

    assert first == again == list(SUIVI_STEPS)
    assert kit == kit_again == list(KIT_STEPS)


async def test_missing_prerequisites_are_said_in_french(api: httpx.AsyncClient) -> None:
    with pytest.raises(CheckFailed) as failed:
        await run_check(api, part="suivi", timeout_s=60, logs="")

    assert failed.value.step == "fiche depuis offre"
    assert "phase 6" in str(failed.value)


async def test_logs_step_fails_without_logs_or_with_personal_data(
    api: httpx.AsyncClient, phase6: None
) -> None:
    with pytest.raises(CheckFailed) as missing:
        await run_check(api, part="kit", timeout_s=300, logs=None)
    assert missing.value.step == "journaux"

    with pytest.raises(CheckFailed) as leaked:
        await run_check(api, part="kit", timeout_s=300, logs="Atelier Relance 1 a été créé")
    assert leaked.value.step == "journaux"
    assert "Atelier" not in str(leaked.value)  # le message ne recopie pas ce qui a fuité


async def test_unknown_part_is_refused(api: httpx.AsyncClient) -> None:
    with pytest.raises(CheckFailed) as refused:
        await run_check(api, part="autre", timeout_s=10)  # type: ignore[arg-type]
    assert refused.value.step == "partie"


@pytest.mark.parametrize(
    ("letter_reply", "message"),
    [
        (json.dumps({"text": "Bonjour, " + "je construis des solutions fiables " * 33}), "mot(s)"),
        (english_letter(), "langue de l'offre"),
    ],
    ids=["trop courte", "autre langue"],
)
@pytest.mark.timeout(600)
async def test_kit_fails_on_a_letter_outside_the_rules(
    api: httpx.AsyncClient, phase6: None, message: str
) -> None:
    await run_check(api, part="suivi", timeout_s=300, logs="")

    with pytest.raises(CheckFailed) as failed:
        await run_check(api, part="kit", timeout_s=300, logs="")

    assert failed.value.step == "kit"
    assert message in str(failed.value)
    assert "construis" not in str(failed.value) and "reliable" not in str(failed.value)
