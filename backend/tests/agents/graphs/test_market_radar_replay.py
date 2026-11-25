"""Parcours `market_radar` : rejeu après un arrêt (pas de relecture ni de réextraction),
journaux sans lien ni texte, et branchement du parcours (registre, route, port non branché)."""

import asyncio
import logging

import pytest

from app.agents.graphs.market_radar import MarketRadarInput
from app.agents.graphs.registry import get_graph
from app.agents.runtime.ports import NO_PORTS
from app.agents.tools.radar_port import NO_RADAR
from app.core.errors import AppError
from app.features.sessions.service import ROUTE_ONLY
from tests.agents.graphs.radar_support import (
    MakeRadar,
    analyst,
    analyst_prompts,
    batch,
    blocked,
    postings,
)
from tests.agents.runtime.runner_helpers import wait_until
from tests.support.radar import ROLE, RUN_ID, ZONE, FakeRadarStore

GUARD = 120.0  # garde contre un blocage, jamais un délai à tenir


async def test_replay_mid_read_never_rereads(
    radar_runner: MakeRadar, radar_store: FakeRadarStore
) -> None:
    """Aucune course d'horloge : on attend le signal « la lecture est figée » (posé par le faux
    port à la 21e lecture, quand 20 sont faites), puis la fin de la session ; `GUARD` n'est qu'une
    garde contre un blocage, pas un délai que la charge de la machine peut faire expirer."""
    radar_store.block_reads_after = 20
    first = await radar_runner(sources=postings(70))
    async with asyncio.timeout(GUARD):
        await radar_store.read_blocked.wait()
    assert len(radar_store.read) == 20
    await first.runner.shutdown()
    radar_store.block_reads_after = None
    second = await radar_runner(first.models, sid=first.sid)
    assert await second.runner.recover_on_startup() == [first.sid]
    await second.wait_status("completed", timeout=GUARD)
    assert radar_store.fresh_reads == 50 and radar_store.repeat_reads == 0
    assert radar_store.queries == 12 and len(first.web.searches) == 12  # recherche pas refaite


async def test_replay_mid_extract_never_reextracts(
    radar_runner: MakeRadar, radar_store: FakeRadarStore
) -> None:
    first_models = analyst()
    first_models.block = lambda agent, _prompt: agent == "analyst" and len(first_models.calls) >= 1
    first = await radar_runner(first_models, sources=postings(12))
    await wait_until(lambda: radar_store.extraction_calls == 1 and first_models.blocked == 1)
    await first.runner.shutdown()
    second_models = analyst(batch(5), batch(2))
    second = await radar_runner(second_models, sid=first.sid)
    assert await second.runner.recover_on_startup() == [first.sid]
    await second.wait_status("completed")
    assert len(first_models.calls) == 1 and len(analyst_prompts(second_models)) == 2
    assert radar_store.extraction_calls == 3 and sorted(radar_store.saved) == sorted(
        f"r{n}" for n in range(1, 13)
    )
    assert radar_store.fresh_reads == 12 and radar_store.repeat_reads == 0


async def test_radar_never_logs_urls_or_text(
    caplog: pytest.LogCaptureFixture, radar_runner: MakeRadar, radar_store: FakeRadarStore
) -> None:
    caplog.set_level(logging.DEBUG, logger="app")  # nos journaux ; le reste (SQL) n'est pas à nous
    sources = postings(7) + blocked(2)
    run = await radar_runner(analyst(batch(5), batch(2)), sources=sources)
    await run.wait_status("completed")
    logged = "\n".join(r.getMessage() for r in caplog.records if r.name.startswith("app"))
    assert "Batch extracted" in logged and "Reading" in logged  # les journaux existent
    for secret in (
        "example.org",
        "https://",
        ROLE,
        ZONE,
        "Société Fictive",
        "Nous recrutons",
        "45 000",
        "Référence",
    ):
        assert secret not in logged


def test_graph_is_registered_with_its_route() -> None:
    assert ROUTE_ONLY["market_radar"] == "POST /radar/runs"
    spec = get_graph("market_radar")
    assert spec.input_model is MarketRadarInput
    assert MarketRadarInput(run_id=RUN_ID).model_dump() == {"run_id": RUN_ID}
    with pytest.raises(ValueError):
        MarketRadarInput(run_id="court")


async def test_unwired_radar_port_refuses() -> None:
    assert NO_PORTS.radar is NO_RADAR
    with pytest.raises(AppError) as raised:
        await NO_RADAR.context("u", "r")
    assert raised.value.code == "radar_unavailable" and raised.value.status_code == 503
