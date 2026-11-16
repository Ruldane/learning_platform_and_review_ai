"""Parcours `daily_brief` sans modèle : aucune clé configurée (8.5, revue : chemin « sans clé ») et
une panne brute de lecture d'une page (le repli sur le résultat suivant ne saute jamais)."""

from tests.agents.graphs.brief_support import (
    FakeBriefWeb,
    MakeBrief,
    NoKeyModels,
    brief_models,
    pick,
)
from tests.support.brief import FakeBriefStore


async def test_without_a_key_both_rubrics_are_empty_and_the_advice_says_unavailable(
    brief_runner: MakeBrief, brief_store: FakeBriefStore, brief_web: FakeBriefWeb
) -> None:
    models = NoKeyModels()
    run = await brief_runner(models)
    await run.wait_status("completed")  # le parcours finit : les rubriques du code sont ailleurs
    assert brief_store.resource is None and brief_store.resource_saved
    assert brief_store.advice is None and brief_store.advice_saved
    assert brief_store.advice_unavailable is True  # « indisponible », pas « échoué »
    assert models.calls == [] and set(models.asked) == {"scout", "moderator"}


async def test_without_a_key_the_web_search_is_not_run(
    brief_runner: MakeBrief, brief_store: FakeBriefStore, brief_web: FakeBriefWeb
) -> None:
    run = await brief_runner(NoKeyModels())
    await run.wait_status("completed")
    assert brief_web.searches == [] and brief_web.reads == []  # le modèle d'abord, le web ensuite


async def test_a_model_that_answers_badly_is_failed_not_unavailable(
    brief_runner: MakeBrief, brief_store: FakeBriefStore
) -> None:
    run = await brief_runner(brief_models([pick(1)], ["pas du json"] * 3))
    await run.wait_status("completed")
    assert brief_store.advice is None and brief_store.advice_saved
    assert brief_store.advice_unavailable is False


async def test_a_raw_error_on_one_page_falls_back_to_the_next_result(
    brief_runner: MakeBrief, brief_store: FakeBriefStore, brief_web: FakeBriefWeb
) -> None:
    brief_web.read_errors = {brief_web.results[1].url: RuntimeError("panne brute du lecteur")}
    run = await brief_runner(brief_models([pick(2)]))
    await run.wait_status("completed")
    first = brief_web.results[0]
    assert brief_web.reads == [brief_web.results[1].url, first.url]  # le repli n'est pas sauté
    assert brief_store.resource is not None and brief_store.resource.url == first.url
    assert brief_store.advice is not None


async def test_three_raw_errors_empty_the_resource_only(
    brief_runner: MakeBrief, brief_store: FakeBriefStore, brief_web: FakeBriefWeb
) -> None:
    brief_web.read_errors = {hit.url: ValueError("x") for hit in brief_web.results}
    run = await brief_runner(brief_models([pick(1)]))
    await run.wait_status("completed")
    assert len(brief_web.reads) == 3 and brief_store.resource is None
    assert brief_store.resource_saved and brief_store.advice is not None
