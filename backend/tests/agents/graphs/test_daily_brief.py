"""Parcours `daily_brief` (P11, D161) : la ressource du jour (l'Éclaireur choisit, le code lit la
page) et le conseil du Modérateur ; les deux appels, les replis sans nouvel appel, les rubriques
vides (sans sujet, recherche en panne) et l'indépendance des deux rubriques."""

import pytest

from app.agents.nodes import moderator_brief
from app.agents.nodes.scout import brief_resource
from app.agents.nodes.scout.brief_resource import FALLBACK_WHY
from app.agents.tools.brief_schema import ResourceView
from app.core.errors import AppError
from tests.agents.graphs.brief_support import (
    GOOD,
    FakeBriefWeb,
    MakeBrief,
    advice,
    brief_models,
    good_advice,
    hit,
    hits,
    pick,
)
from tests.support.brief import TOPIC, FakeBriefStore


async def test_brief_graph_two_calls(
    brief_runner: MakeBrief, brief_store: FakeBriefStore, brief_web: FakeBriefWeb
) -> None:
    run = await brief_runner(brief_models([pick(2, "Un guide clair.")], [good_advice()]))
    await run.wait_status("completed")
    found = brief_web.results[1]
    assert brief_store.resource == ResourceView(
        title=found.title,
        url=found.url,
        domain="docs.exemple.org",
        published=found.published,
        why="Un guide clair.",
    )
    assert brief_store.advice == list(GOOD)
    assert len(run.models.calls) == 2 and run.calls("scout") == 1 and run.calls("moderator") == 1
    assert brief_web.searches == [(TOPIC, None, "month")] and brief_web.reads == [found.url]
    [done] = await run.events("run.completed")
    assert done["summary"] == "Your daily brief is ready."
    assert (await run.types())[-1] == "run.completed"


async def test_unreadable_pick_falls_back_without_new_call(
    brief_runner: MakeBrief, brief_store: FakeBriefStore, brief_web: FakeBriefWeb
) -> None:
    brief_web.unreadable = {brief_web.results[1].url}
    run = await brief_runner(brief_models([pick(2, "Le meilleur guide.")]))
    await run.wait_status("completed")
    first = brief_web.results[0]
    assert brief_web.reads == [brief_web.results[1].url, first.url]  # le choix, puis dans l'ordre
    assert brief_store.resource is not None and brief_store.resource.url == first.url
    # la raison du modèle ne suit pas un résultat qu'il n'a pas choisi
    assert brief_store.resource.why == FALLBACK_WHY["fr"]
    assert run.calls("scout") == 1  # aucun nouvel appel au modèle


@pytest.mark.parametrize(
    ("why", "kept"),
    [
        ("Un guide récent, partie 2 de la série.", True),  # le 2 est dans le titre du résultat
        ("Écrit par une équipe avec 10 ans d'expérience.", False),  # rien ne dit ce nombre
        ("Un guide de trois heures pour tout comprendre.", False),  # ni celui-là, en lettres
    ],
)
async def test_resource_reason_never_invents_a_number(
    brief_runner: MakeBrief, brief_store: FakeBriefStore, why: str, kept: bool
) -> None:
    run = await brief_runner(brief_models([pick(2, why)]))
    await run.wait_status("completed")
    assert brief_store.resource is not None
    assert brief_store.resource.why == (why if kept else FALLBACK_WHY["fr"])


async def test_three_reads_at_most_then_empty(
    brief_runner: MakeBrief, brief_store: FakeBriefStore, brief_web: FakeBriefWeb
) -> None:
    brief_web.unreadable = {h.url for h in brief_web.results}
    run = await brief_runner(brief_models([pick(4)]))
    await run.wait_status("completed")
    urls = [h.url for h in brief_web.results]
    assert [urls.index(u) for u in brief_web.reads] == [3, 0, 1]  # le choix (4), puis 1 et 2
    assert brief_store.resource_saved and brief_store.resource is None
    assert brief_store.advice == list(GOOD)  # le conseil ne dépend pas de la ressource


@pytest.mark.parametrize("answer", [pick(None), pick(7)])
async def test_no_pick_reads_nothing(
    brief_runner: MakeBrief, brief_store: FakeBriefStore, brief_web: FakeBriefWeb, answer: str
) -> None:
    # `None` : aucun résultat ne convient ; 7 : un rang qui n'est pas dans les cinq résultats
    run = await brief_runner(brief_models([answer]))
    await run.wait_status("completed")
    assert brief_web.reads == [] and brief_store.resource is None and brief_store.resource_saved
    assert brief_store.advice == list(GOOD)


async def test_page_without_text_is_not_read(
    brief_runner: MakeBrief, brief_store: FakeBriefStore, brief_web: FakeBriefWeb
) -> None:
    brief_web.empty = {brief_web.results[1].url}
    run = await brief_runner(brief_models([pick(2)]))
    await run.wait_status("completed")
    assert brief_store.resource is not None
    assert brief_store.resource.url == brief_web.results[0].url


async def test_no_topic_no_resource(
    brief_runner: MakeBrief, brief_store: FakeBriefStore, brief_web: FakeBriefWeb
) -> None:
    brief_store.topic = None
    run = await brief_runner(brief_models())
    await run.wait_status("completed")
    assert brief_web.searches == [] and run.calls("scout") == 0
    assert brief_store.resource is None and brief_store.resource_saved
    assert brief_store.advice == list(GOOD) and run.calls("moderator") == 1


@pytest.mark.parametrize(
    "error",
    [
        AppError("search_unavailable", "Brut.", 503),
        AppError("web_quota_reached", "Brut.", 429),
        RuntimeError("panne"),
    ],
)
async def test_search_down_keeps_advice(
    brief_runner: MakeBrief, brief_store: FakeBriefStore, brief_web: FakeBriefWeb, error: Exception
) -> None:
    brief_web.search_error = error
    run = await brief_runner(brief_models())
    await run.wait_status("completed")
    assert brief_store.resource is None and brief_store.resource_saves == 1
    assert brief_store.advice == list(GOOD) and run.calls("scout") == 0


async def test_no_valid_results_asks_no_model(
    brief_runner: MakeBrief, brief_store: FakeBriefStore, brief_web: FakeBriefWeb
) -> None:
    brief_web.results = [hit(1, url="ftp://exemple.org/x"), hit(2, url="pas un lien")]
    run = await brief_runner(brief_models())
    await run.wait_status("completed")
    assert run.calls("scout") == 0 and brief_store.resource is None
    assert brief_web.reads == []  # un lien invalide n'est ni montré ni lu


async def test_only_the_first_eight_distinct_results_are_shown(
    brief_runner: MakeBrief, brief_store: FakeBriefStore, brief_web: FakeBriefWeb
) -> None:
    twin = hit(2, url="https://www.docs.exemple.org/guide/1/?utm_source=x")  # même lien que le 1
    brief_web.results = [hit(1), twin, *hits(12)[1:]]
    run = await brief_runner(brief_models([pick(8)]))
    await run.wait_status("completed")
    [shown] = [c for c in run.models.calls if c.agent == "scout"]
    assert "8. Guide LangGraph partie 8" in shown.prompt and "9. Guide" not in shown.prompt
    assert "2. Guide LangGraph partie 2" in shown.prompt  # le doublon n'est pas montré
    assert brief_store.resource is not None and brief_store.resource.url == hits(12)[7].url


async def test_scout_failure_keeps_advice(
    brief_runner: MakeBrief, brief_store: FakeBriefStore
) -> None:
    run = await brief_runner(brief_models(["pas du json"] * 3))
    await run.wait_status("completed")
    assert brief_store.resource is None and brief_store.resource_saved
    assert brief_store.advice == list(GOOD)


async def test_advice_failure_keeps_resource(
    brief_runner: MakeBrief, brief_store: FakeBriefStore
) -> None:
    run = await brief_runner(brief_models([pick(1)], ["pas du json"] * 3))
    await run.wait_status("completed")
    assert brief_store.advice is None and brief_store.advice_saved
    assert brief_store.resource is not None  # la ressource est rangée


async def test_both_rubrics_empty_still_completes(
    brief_runner: MakeBrief, brief_store: FakeBriefStore
) -> None:
    run = await brief_runner(brief_models(["x"] * 3, [advice("Trop court.", "Aussi.")] * 3))
    await run.wait_status("completed")
    assert brief_store.resource is None and brief_store.advice is None
    assert brief_store.resource_saved and brief_store.advice_saved
    [done] = await run.events("run.completed")
    assert done["summary"] == "Your daily brief is ready."


@pytest.mark.parametrize("slow", ["scout", "moderator"])
async def test_a_slow_rubric_is_emptied_not_fatal(
    brief_runner: MakeBrief,
    brief_store: FakeBriefStore,
    monkeypatch: pytest.MonkeyPatch,
    slow: str,
) -> None:
    monkeypatch.setattr(brief_resource, "BUDGET_S", 0.2)
    monkeypatch.setattr(moderator_brief, "BUDGET_S", 0.2)
    models = brief_models([pick(1)])
    models.block = lambda agent, _prompt: agent == slow  # ce modèle ne répond jamais
    run = await brief_runner(models)
    await run.wait_status("completed")
    if slow == "scout":
        assert brief_store.resource is None and brief_store.advice == list(GOOD)
    else:
        assert brief_store.advice is None and brief_store.resource is not None
    assert brief_store.resource_saved and brief_store.advice_saved
