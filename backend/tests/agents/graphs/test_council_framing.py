"""Parcours `learning_council`, première moitié (D84) : cadrage du Modérateur (point d'arrêt
n° 1), recherche de l'Éclaireur et praticiens. Chaque session va ensuite jusqu'au choix du
parcours avec le débat par défaut des faux modèles (D85). Faux LLM, faux moteurs, vraie base."""

import asyncio
import json
import logging

import pytest

from app.agents.nodes.moderator import framing_answers, research_query
from app.agents.nodes.scout.people import _url_key
from app.agents.tools.web_port import PersonFound
from app.features.research.repository import SourceRepository
from tests.agents.graphs.council_models import URLS, CouncilModels
from tests.agents.graphs.council_support import (
    ADA_URL,
    PAGE_COUNT,
    Council,
    MakeCouncil,
    framing_replies,
    research_replies,
)
from tests.agents.runtime.runner_helpers import wait_until
from tests.support.council import GOAL_TEXT

START = "<<<CONTENU_NON_FIABLE"
END = "<<<FIN_CONTENU_NON_FIABLE>>>"
ANSWER = "Je vise un poste en startup"
PEOPLE_MARKER = "Repère les praticiens."


def _people(*names: str) -> str:
    return json.dumps(
        {
            "people": [
                {"name": n, "role": "Ingénieure", "urls": [URLS[i]]} for i, n in enumerate(names)
            ]
        }
    )


TWO_PEOPLE = _people("Ada Lovelace", "Grace Hopper")
OTHER_PEOPLE = _people("Alan Turing", "Margaret Hamilton", "Barbara Liskov")


async def _people_rows(c: Council) -> list[str]:
    async with c.web.factory() as db:
        rows = await SourceRepository(db, c.user_id).list_for_session(c.sid)
    return [r.title or "" for r in rows if r.kind == "person"]


async def test_council_stops_at_framing_with_fields(make_council_runner: MakeCouncil) -> None:
    c = await make_council_runner(framing_replies(3))
    view = await c.wait_status("waiting_user")
    pending = view.pending_interrupt or {}
    assert pending["kind"] == "framing"
    assert [f["id"] for f in pending["fields"]] == ["q1", "q2", "q3"]
    assert pending["fields"][0]["label"] == "Question de cadrage numéro 1 ?"
    assert pending["options"] == [{"value": "go", "label": "Lancer la recherche"}]
    assert c.store.framing_saved == [] and c.web.search.calls == []  # rien avant la réponse
    assert GOAL_TEXT in c.prompts()[0]  # le Modérateur a lu l'objectif


async def test_framing_never_more_than_five_questions(make_council_runner: MakeCouncil) -> None:
    c = await make_council_runner(framing_replies(7) + framing_replies(2))
    view = await c.wait_status("waiting_user")
    assert [f["id"] for f in (view.pending_interrupt or {})["fields"]] == ["q1", "q2"]
    assert len(c.prompts()) == 2  # 7 questions : schéma refusé, second essai


async def test_zero_question_still_stops(make_council_runner: MakeCouncil) -> None:
    c = await make_council_runner(framing_replies(0) + research_replies())
    view = await c.wait_status("waiting_user")
    assert (view.pending_interrupt or {})["fields"] == []
    assert c.web.search.calls == []
    await c.resume("go")
    await c.wait_choice()
    assert c.store.framing_saved == [([], {})]


async def test_answers_are_saved_and_feed_the_research_query(
    make_council_runner: MakeCouncil,
) -> None:
    c = await make_council_runner(framing_replies(2) + research_replies())
    await c.wait_status("waiting_user")
    await c.resume({"answers": {"q1": ANSWER, "q9": "inconnue"}})
    await c.wait_choice()
    questions, answers = c.store.framing_saved[-1]
    assert answers == {"q1": ANSWER}
    assert [q["id"] for q in questions] == ["q1", "q2"]
    assert "startup" in c.search_queries_prompt()
    assert GOAL_TEXT in c.search_queries_prompt()


async def test_framing_answer_saved_once_after_replay(
    make_council_runner: MakeCouncil,
) -> None:
    # Le port se fige juste après l'écriture des réponses : arrêt du back en plein
    # `apply_framing`, que la reprise rejoue depuis son début.
    first = await make_council_runner(framing_replies(2))
    first.store.block_after_framing = True
    await first.wait_status("waiting_user")
    await first.resume({"answers": {"q2": ANSWER}})
    await wait_until(lambda: first.store.framing_calls == 1)
    await first.runner.shutdown()
    first.store.block_after_framing = False
    second = await make_council_runner(research_replies(), sid=first.sid)
    assert await second.runner.recover_on_startup() == [first.sid]
    await second.wait_choice()
    assert second.store.framing_calls == 2  # nœud rejoué…
    assert len(second.store.framing_saved) == 1  # … sans seconde écriture différente
    assert second.store.framing_saved[0][1] == {"q2": ANSWER}
    assert "startup" in second.search_queries_prompt()
    assert "Prépare les requêtes de recherche." in second.prompts()[0]
    framing = "Prépare les questions de cadrage."
    assert not [p for p in second.prompts() if framing in p]  # Modérateur non rappelé


async def test_research_scores_sources_and_spots_people(make_council_runner: MakeCouncil) -> None:
    c = await make_council_runner(framing_replies(1) + research_replies())
    await c.wait_status("waiting_user")
    await c.resume("go")
    await c.wait_choice()
    found = await c.source_found()
    assert sum(1 for f in found if f["kind"] == "page" and f["score"] is not None) >= 8
    people = [f for f in found if f["kind"] == "person"]
    assert {f["title"] for f in people} == {"Ada Lovelace"}
    ada = people[0]
    assert (ada["url"], ada["role"], ada["verdict"], ada["score"]) == (
        ADA_URL,
        "Ingénieure IA",
        "kept",
        None,
    )
    assert await _people_rows(c) == ["Ada Lovelace"]


async def test_person_without_read_url_is_dropped(make_council_runner: MakeCouncil) -> None:
    invented = json.dumps(
        {"people": [{"name": "Inventée", "role": "Ingénieure", "urls": ["https://x.exemple/"]}]}
    )
    c = await make_council_runner(framing_replies(1) + research_replies(invented))
    await c.wait_status("waiting_user")
    await c.resume("go")
    await c.wait_choice()
    assert [f for f in await c.source_found() if f["kind"] == "person"] == []
    assert await _people_rows(c) == []


async def test_people_prompt_frames_page_metadata_as_untrusted(
    make_council_runner: MakeCouncil,
) -> None:
    c = await make_council_runner(framing_replies(1) + research_replies())
    await c.wait_status("waiting_user")
    await c.resume("go")
    await c.wait_choice()
    prompt = c.people_prompt()
    assert prompt.count(END) >= PAGE_COUNT + 1  # chaque page, plus la règle partagée
    line = prompt.index("Auteur : Ada Lovelace")
    assert prompt.rfind(START, 0, line) > prompt.rfind(END, 0, line)  # encadré


async def test_people_node_stopped_midway_is_replayed_without_the_model(
    make_council_runner: MakeCouncil,
) -> None:
    # Le modèle rend deux praticiens ; le back s'arrête juste après l'écriture du premier (en
    # plein `spot_people`). À la reprise, une autre réponse du modèle ajouterait d'autres
    # personnes : le nœud réémet celle déjà écrite sans rappeler le modèle.
    models = CouncilModels()
    models.when("scout", PEOPLE_MARKER, TWO_PEOPLE)
    first = await make_council_runner(models=models)
    written: list[str] = []
    add_person = first.web.gateway.add_person

    async def add_then_stop(user_id: str, session_id: str, person: PersonFound) -> str:
        written.append(await add_person(user_id, session_id, person))
        await asyncio.Event().wait()
        raise AssertionError("jamais atteint")

    first.web.gateway.add_person = add_then_stop  # type: ignore[method-assign]
    await first.wait_question("framing")
    await first.resume("go")
    await wait_until(lambda: len(written) == 1)
    await first.runner.shutdown()
    again = CouncilModels()
    again.when("scout", PEOPLE_MARKER, OTHER_PEOPLE)
    second = await make_council_runner(models=again, sid=first.sid)
    assert await second.runner.recover_on_startup() == [first.sid]
    await second.wait_choice()
    assert not [p for p in second.prompts() if PEOPLE_MARKER in p]  # modèle non rappelé
    assert await _people_rows(second) == ["Ada Lovelace"]  # aucune ligne de plus
    people = [f for f in await second.source_found() if f["kind"] == "person"]
    assert {f["source_id"] for f in people} == set(written)  # réémise à l'identique
    assert len(people) <= 10


async def test_logs_never_contain_goal_text_or_answers(
    make_council_runner: MakeCouncil, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)
    caplog.set_level(logging.DEBUG, logger="app")
    c = await make_council_runner(framing_replies(2) + research_replies())
    await c.wait_status("waiting_user")
    await c.resume({"answers": {"q1": ANSWER}})
    await c.wait_choice()
    await asyncio.sleep(0)
    for secret in (GOAL_TEXT, ANSWER, "Question de cadrage", "Ada Lovelace", ADA_URL):
        assert secret not in caplog.text


def test_framing_answers_accepts_only_the_answers_object() -> None:
    ids = ["q1", "q2"]
    assert framing_answers("go", ids) == {}
    assert framing_answers({"q1": "x"}, ids) == {}
    assert framing_answers({"answers": ["x"]}, ids) == {}
    long = "a" * 2500
    got = framing_answers({"answers": {"q1": f"  {long} ", "q2": "  ", "q3": "z", "q4": 3}}, ids)
    assert got == {"q1": "a" * 2000}
    assert framing_answers({"answers": {"q2": 7}}, ids) == {}


def test_research_query_is_one_line_of_300_chars_at_most() -> None:
    goal = {"text": "Devenir\nAI   engineer", "target_role": "ML engineer"}
    questions = [{"id": "q1", "question": "?"}, {"id": "q2", "question": "?"}]
    query = research_query(goal, questions, {"q2": "startup\nparisienne", "q1": "x" * 400})
    assert "\n" not in query and len(query) <= 300
    assert query.startswith("Devenir AI engineer ; ML engineer ; x")
    assert research_query({"text": "Data", "target_role": None}, [], {}) == "Data"


def test_url_key_folds_scheme_and_host_only() -> None:
    assert _url_key("HTTPS://Site.Exemple.org/Doc/") == _url_key("https://site.exemple.org/Doc")
    assert _url_key("https://site.exemple.org/Doc") != _url_key("https://site.exemple.org/doc")
    assert _url_key("https://a.org/p?Q=1#frag") == "https://a.org/p?Q=1"
