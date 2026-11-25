"""Pannes du radar (D173) : sans modèle le relevé échoue tout de suite ; une panne du fournisseur
sur un lot ne perd pas les autres, et deux lots en panne arrêtent l'extraction."""

import pytest

from app.agents.nodes.analyst_radar import RADAR_REQUEST
from app.agents.nodes.scout.radar_text import NO_ANALYSIS_TEXT, NO_MODEL_TEXT
from app.agents.tools.radar_port import RadarSummary
from app.core.errors import AppError
from tests.agents.graphs.radar_support import MakeRadar, analyst, analyst_prompts, batch, postings
from tests.support.radar import FakeRadarStore


async def test_no_model_fails_early_before_any_search_or_read(
    radar_runner: MakeRadar, radar_store: FakeRadarStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sans clé, le relevé échoue dès `load` (D173) : aucune recherche, aucune page lue."""
    models = analyst()

    async def no_key(user_id: str, tier: object, agent: str | None = None) -> object:
        raise AppError("llm_key_missing", "Aucune clé.", 400)

    monkeypatch.setattr(models, "get_chat_model", no_key)
    run = await radar_runner(models, sources=postings(5))
    await run.wait_status("failed")
    [failed] = await run.events("run.failed")
    assert failed == {"code": "llm_unavailable", "message": NO_MODEL_TEXT}
    assert radar_store.fail_codes == ["llm_unavailable"]
    assert run.web.searches == [] and radar_store.fresh_reads == 0
    assert analyst_prompts(models) == [] and radar_store.summary is None


async def test_provider_error_on_a_batch_fails_it_and_continues_then_stops_after_two(
    radar_runner: MakeRadar, radar_store: FakeRadarStore
) -> None:
    """Une panne du fournisseur sur un lot ne perd pas les autres lots ; deux lots en panne
    arrêtent l'extraction, le reste est lu mais pas analysé (D173)."""
    models = analyst(batch(5), default=0)

    async def down(agent: str, prompt: str) -> None:
        if RADAR_REQUEST in prompt and "posting p1" in prompt and len(analyst_prompts(models)) >= 1:
            raise AppError("llm_timeout", "Trop long.", 504)

    models.hooks.append(down)
    run = await radar_runner(models, sources=postings(25))
    await run.wait_status("completed")
    assert sorted(radar_store.saved) == ["r1", "r2", "r3", "r4", "r5"]  # le premier lot est gardé
    assert radar_store.failed == [f"r{n}" for n in range(6, 16)]  # deux lots en panne
    assert radar_store.summary == RadarSummary(25, 0, 0, 5, True)  # les 10 derniers : pas analysés


async def test_every_batch_failing_ends_the_run_failed_with_analysis_failed(
    radar_runner: MakeRadar, radar_store: FakeRadarStore
) -> None:
    """Deux lots en panne et aucune offre analysée : le relevé échoue (`analysis_failed`), il n'est
    pas « terminé » à vide : la règle des relevés en échec repris dans la semaine s'applique."""
    models = analyst()

    async def down(agent: str, prompt: str) -> None:
        if RADAR_REQUEST in prompt:
            raise AppError("llm_timeout", "Trop long.", 504)

    models.hooks.append(down)
    run = await radar_runner(models, sources=postings(25))
    await run.wait_status("failed")
    [failed] = await run.events("run.failed")
    assert failed == {"code": "analysis_failed", "message": NO_ANALYSIS_TEXT}
    assert radar_store.saved == {} and radar_store.summary is not None
    assert radar_store.summary.error_code == "analysis_failed" and radar_store.summary.analyzed == 0
    assert await run.events("artifact.ready") == []  # aucun relevé à ouvrir
