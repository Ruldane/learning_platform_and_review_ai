"""Scénario du parcours n° 4 : les réponses scriptées passent la vraie validation des schémas du
brief et du radar, le web factice donne ce que le parcours annonce (8 offres lisibles, 3 pages
bloquées, 11 liens), et chaque réponse n'est servie qu'à son appel."""

import json
from pathlib import Path

import pytest
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.nodes import moderator_brief
from app.agents.nodes.analyst_radar import RADAR_REQUEST, clean_batch, radar_vars
from app.agents.nodes.scout import brief_resource
from app.agents.nodes.scout.brief_resource import usable_hits, why_of
from app.agents.nodes.scout.radar import candidates
from app.agents.prompts.loader import render_prompt
from app.agents.tools.brief_schema import CouncilAdvice, ResourcePick, numbers_in_advice
from app.agents.tools.radar_port import PostingPage
from app.agents.tools.radar_schema import RadarBatch, link_key, radar_searches
from app.agents.tools.web_port import WebHit
from app.providers.search.fake import FakeSearch
from app.providers.web.base import WebDocument
from tests.e2e import daily_script
from tests.e2e.applications_script import applications_scripts
from tests.e2e.council_script import council_scripts
from tests.e2e.cv_script import cv_scripts
from tests.e2e.daily_script import (
    ADVICE_REQUEST,
    BLOCKED_URLS,
    LANGUAGES,
    OFFER_URLS,
    OFFERS,
    PICK_REQUEST,
    PICKED_RESOURCE,
    ROLE,
    TOPIC_QUERY,
    WHY,
    ZONE,
    daily_scripts,
    offer_text,
    script_daily_web,
)
from tests.e2e.scripted_models import ScriptedModels, merge_scripts
from tests.support.memory import FakeWebReader


def _web() -> tuple[FakeWebReader, FakeSearch]:
    reader, search = FakeWebReader(), FakeSearch("searxng")
    script_daily_web(reader, search)
    return reader, search


def _pages(*numbers: int) -> list[PostingPage]:
    """Les pages d'un lot, dans un ordre qui n'est PAS celui des offres (les lectures
    simultanées finissent dans l'ordre qu'elles veulent)."""
    return [
        PostingPage(f"p{ref}", OFFER_URLS[number - 1], "emplois-fictifs.example.org", "ok",
                    offer_text(number))
        for ref, number in enumerate(numbers, start=1)
    ]  # fmt: skip


async def _ask(models: ScriptedModels, agent: str, system: str, request: str) -> str:
    model = await models.get_chat_model("u1", "fast", agent=agent)
    reply = await model.ainvoke([SystemMessage(system), HumanMessage(request)])
    return str(reply.content)


# --- Brief -----------------------------------------------------------------------------------


def test_the_requests_are_the_ones_the_nodes_send() -> None:
    assert PICK_REQUEST in Path(brief_resource.__file__).read_text(encoding="utf-8")
    assert ADVICE_REQUEST in Path(moderator_brief.__file__).read_text(encoding="utf-8")


async def test_the_pick_and_the_advice_pass_the_real_schemas() -> None:
    models = ScriptedModels(daily_scripts())

    pick = ResourcePick.model_validate_json(await _ask(models, "scout", "Sujet.", PICK_REQUEST))
    advice = CouncilAdvice.model_validate_json(
        await _ask(models, "moderator", "Faits.", ADVICE_REQUEST)
    )

    assert pick.index == daily_script.PICKED
    assert numbers_in_advice(advice.sentences) == set()  # aucun nombre : jamais refusé par le code
    assert len(advice.sentences) == 2


def test_the_topic_query_is_what_the_brief_searches_and_the_pick_is_read() -> None:
    reader, search = _web()
    hits = [
        WebHit(r.title, r.url, r.snippet, r.engine, r.published, preferred=False)
        for r in search.results[TOPIC_QUERY]
    ]
    shown = usable_hits(hits)
    picked = shown[daily_script.PICKED - 1]
    page = reader.pages[picked.url]

    assert len(shown) == len(hits) == 3
    assert picked.url == PICKED_RESOURCE.url
    assert isinstance(page, WebDocument) and page.text.strip()
    assert picked.url != shown[0].url and shown[0].url not in reader.pages  # le 1er est illisible
    pick = ResourcePick(index=daily_script.PICKED, why=WHY)
    assert why_of(pick, picked, "fr") == WHY  # la raison n'a aucun nombre : gardée telle quelle


# --- Radar -----------------------------------------------------------------------------------


def test_the_search_gives_eleven_links_of_which_three_are_blocked() -> None:
    reader, search = _web()
    queries = [s.query for s in radar_searches(ROLE, ZONE, LANGUAGES)]
    found = [[hit.url for hit in search.results.get(query, [])] for query in queries]
    urls = candidates(found)

    assert [len(chunk) for chunk in found[:2]] == [6, 5]
    assert len(urls) == len({link_key(url) for url in urls}) == 11
    assert sorted(urls) == sorted([*OFFER_URLS, *BLOCKED_URLS])
    assert all(url in reader.pages for url in OFFER_URLS)
    assert not any(url in reader.pages for url in BLOCKED_URLS)  # illisibles : « bloquées »
    assert len(OFFERS) == len(OFFER_URLS) == 8


@pytest.mark.parametrize("numbers", [(1, 2, 3, 4, 5), (8, 6, 7), (7, 3, 5, 1, 8)])
async def test_the_batch_is_read_by_the_reference_of_each_page_not_by_its_place(
    numbers: tuple[int, ...],
) -> None:
    pages = _pages(*numbers)
    system = render_prompt("analyst", **radar_vars(pages))
    models = ScriptedModels(daily_scripts())

    reply = await _ask(models, "analyst", system, RADAR_REQUEST)
    batch = RadarBatch.model_validate_json(reply)
    findings, failed, ignored = clean_batch(batch, pages)

    assert (failed, ignored) == ([], 0)
    for page, finding, number in zip(pages, findings, numbers, strict=True):
        offer = OFFERS[number - 1]
        assert finding.ref == page.ref
        assert finding.title == offer.title
        assert finding.level == offer.level
        assert finding.tools == list(offer.tools)  # le code ne retire aucun outil : ils sont lus
        assert finding.salary == offer.salary  # ni un salaire : ses chiffres sont dans la page
        assert [s.name for s in finding.skills] == [name for name, _ in offer.skills]


def test_one_offer_shows_a_salary_and_the_others_none() -> None:
    assert [offer.salary is not None for offer in OFFERS] == [True] + [False] * 7
    assert OFFERS[0].salary is not None and OFFERS[0].salary in offer_text(1)


def test_an_unknown_page_stops_the_script_naming_the_cause() -> None:
    with pytest.raises(RuntimeError, match="n'est pas une offre du parcours"):
        daily_script.radar_item("p1", "Une page sans référence.")


# --- Les files ne se volent pas leurs appels ------------------------------------------------


async def test_each_reply_is_served_to_its_call_when_the_scenarios_are_merged() -> None:
    models = ScriptedModels(
        merge_scripts(daily_scripts(), applications_scripts(), council_scripts(), cv_scripts())
    )
    pages = _pages(1, 2)
    system = render_prompt("analyst", **radar_vars(pages))

    batch = RadarBatch.model_validate_json(await _ask(models, "analyst", system, RADAR_REQUEST))
    advice = json.loads(await _ask(models, "moderator", "Faits.", ADVICE_REQUEST))

    assert [item.ref for item in batch.items] == ["p1", "p2"]
    assert advice["sentences"] == daily_script.SENTENCES


async def test_the_queues_cover_every_call_and_retry_of_the_journey() -> None:
    models = ScriptedModels(daily_scripts())
    pages = _pages(1, 2)
    system = render_prompt("analyst", **radar_vars(pages))

    for _ in range(daily_script.LONG):
        await _ask(models, "analyst", system, RADAR_REQUEST)
        await _ask(models, "scout", "Sujet.", PICK_REQUEST)
        await _ask(models, "moderator", "Faits.", ADVICE_REQUEST)

    assert models.remaining() == {}
