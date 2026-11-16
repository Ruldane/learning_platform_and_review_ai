"""Parcours `daily_brief` : rejeu après un arrêt (la ressource rangée n'est pas redemandée),
journaux sans sujet ni texte, et branchement du parcours (registre, route, port non branché)."""

import logging

import pytest

from app.agents.graphs.daily_brief import DailyBriefInput
from app.agents.graphs.registry import get_graph
from app.agents.runtime.ports import NO_PORTS
from app.agents.tools.brief_port import NO_BRIEF
from app.core.errors import AppError
from app.features.sessions.service import ROUTE_ONLY
from tests.agents.graphs.brief_support import (
    ADVICE_MARKER,
    FakeBriefWeb,
    MakeBrief,
    brief_models,
    good_advice,
    pick,
)
from tests.agents.runtime.runner_helpers import wait_until
from tests.support.brief import BLOCK, BRIEF_ID, FACTS, TOPIC, FakeBriefStore


async def test_replay_after_resource_skips_it(
    brief_runner: MakeBrief, brief_store: FakeBriefStore, brief_web: FakeBriefWeb
) -> None:
    first_models = brief_models([pick(2)])
    first_models.block = lambda agent, _prompt: agent == "moderator"  # arrêt avant le conseil
    first = await brief_runner(first_models)
    await wait_until(lambda: first_models.blocked == 1 and brief_store.resource_saved)
    await first.runner.shutdown()
    second_models = brief_models([pick(2)])  # un second appel de l'Éclaireur serait vu ici
    second = await brief_runner(second_models, sid=first.sid)
    assert await second.runner.recover_on_startup() == [first.sid]
    await second.wait_status("completed")
    assert first.calls("scout") == 1 and second.calls("scout") == 0  # pas de second appel
    assert len(brief_web.searches) == 1 and len(brief_web.reads) == 1  # ni recherche ni lecture
    assert brief_store.resource_saves == 1 and brief_store.advice_saves == 1
    assert brief_store.resource is not None and brief_store.advice is not None


async def test_rubrics_already_stored_are_skipped(
    brief_runner: MakeBrief, brief_store: FakeBriefStore, brief_web: FakeBriefWeb
) -> None:
    # le port dit « déjà rangé » (écriture faite, point de contrôle perdu) : rien n'est refait
    brief_store.resource_saved = brief_store.advice_saved = True
    run = await brief_runner(brief_models())
    await run.wait_status("completed")
    assert run.models.calls == [] and brief_web.searches == [] and brief_web.reads == []
    assert brief_store.resource_saves == 0 and brief_store.advice_saves == 0
    [done] = await run.events("run.completed")
    assert done["summary"] == "Brief du jour prêt."


async def test_replay_with_only_the_advice_missing(
    brief_runner: MakeBrief, brief_store: FakeBriefStore, brief_web: FakeBriefWeb
) -> None:
    brief_store.resource_saved = True  # la ressource est rangée (même vide) : on ne la refait pas
    run = await brief_runner(brief_models([], [good_advice()]))
    await run.wait_status("completed")
    assert run.calls("scout") == 0 and brief_web.searches == []
    assert run.calls("moderator") == 1 and brief_store.advice is not None


async def test_brief_graph_never_logs_texts(
    caplog: pytest.LogCaptureFixture,
    brief_runner: MakeBrief,
    brief_store: FakeBriefStore,
    brief_web: FakeBriefWeb,
) -> None:
    caplog.set_level(logging.DEBUG, logger="app")  # nos journaux ; le reste (SQL) n'est pas à nous
    brief_web.unreadable = {brief_web.results[1].url}
    why = "Phrase secrète du choix."
    run = await brief_runner(brief_models([pick(2, why)]))
    await run.wait_status("completed")
    logged = "\n".join(r.getMessage() for r in caplog.records if r.name.startswith("app"))
    assert "Ressource du brief rangée" in logged and "Conseil du brief rangé" in logged
    secrets = [TOPIC, BLOCK, why, "exemple.org", "https://", "Guide LangGraph", "Extrait du guide"]
    secrets += ["Commence par ton bloc", "tes 12 fiches", FACTS.block_title or ""]
    for secret in secrets:
        assert secret not in logged
    assert ADVICE_MARKER not in logged


async def test_failed_rubric_logs_only_a_code(
    caplog: pytest.LogCaptureFixture,
    brief_runner: MakeBrief,
    brief_web: FakeBriefWeb,
) -> None:
    caplog.set_level(logging.DEBUG, logger="app")
    brief_web.search_error = AppError("search_unavailable", "Brut secret.", 503)
    run = await brief_runner(brief_models())
    await run.wait_status("completed")
    logged = "\n".join(r.getMessage() for r in caplog.records if r.name.startswith("app"))
    assert "cause search_unavailable" in logged and "Brut secret" not in logged


def test_graph_is_registered_with_its_route() -> None:
    assert ROUTE_ONLY["daily_brief"] == "GET /brief/today"
    spec = get_graph("daily_brief")
    assert spec.input_model is DailyBriefInput and spec.recursion_limit is None
    assert DailyBriefInput(brief_id=BRIEF_ID).model_dump() == {"brief_id": BRIEF_ID}
    with pytest.raises(ValueError):
        DailyBriefInput(brief_id="court")


async def test_unwired_brief_port_refuses() -> None:
    assert NO_PORTS.brief is NO_BRIEF
    with pytest.raises(AppError) as raised:
        await NO_BRIEF.context("u", "b")
    assert raised.value.code == "brief_unavailable" and raised.value.status_code == 503
    for call in (
        NO_BRIEF.save_resource("u", "s", "b", None),
        NO_BRIEF.save_advice("u", "s", "b", None),
    ):
        with pytest.raises(AppError) as refused:
            await call
        assert refused.value.code == "brief_unavailable"
