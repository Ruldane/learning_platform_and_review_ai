"""Révisions du Rédacteur qui n'abîment plus le chapitre (étape 3, pilote du 22/11, D305) :
une révision part de la meilleure version contrôlée, et la consigne de révision est ciblée
(longueur de départ, borne, critères déjà réussis à préserver)."""

from app.agents.nodes.verifier.verify import draft_rank
from tests.agents.graphs.council_models import URLS
from tests.agents.graphs.lesson_support import MakeLesson, claims
from tests.support.lessons import lesson_markdown

FIRST = lesson_markdown(2000, urls=(URLS[0], URLS[1]))  # seule à contenir « notion1800 »
WORSE = lesson_markdown(900, urls=(URLS[0], URLS[1]))  # trop courte : un problème de contrôle
CLAIM = "Le softmax date de 1990 sans aucune source."


def test_rank_puts_check_problems_before_unsupported_claims() -> None:
    fifteen_claims = draft_rank(problems=[], unsupported=["c"] * 15, scores={"a": 80})
    one_problem = draft_rank(problems=["p"], unsupported=[], scores={"a": 90})
    assert fifteen_claims < one_problem


def test_rank_breaks_ties_on_the_lowest_grade() -> None:
    low = draft_rank(problems=[], unsupported=["c"], scores={"a": 90, "b": 70})
    high = draft_rank(problems=[], unsupported=["c"], scores={"a": 80, "b": 78})
    assert high < low


async def test_worse_revision_is_dropped_and_the_next_starts_from_the_best(
    make_lesson_runner: MakeLesson,
) -> None:
    c = await make_lesson_runner(writer=[FIRST, WORSE], verifier=[claims(CLAIM)])
    await c.wait_status("completed")

    assert c.writer_calls == 3
    third = c.prompt_of_writer(3)
    assert "notion1800" in third  # la meilleure version, pas la dernière
    assert f"Affirmation non sourcée : {CLAIM}" in third
    assert "La leçon fait 900 mots" not in third
    texts = [e["text"] for e in await c.events("agent.message") if "text" in e]
    assert any("moins bonne que la précédente" in text for text in texts)


async def test_revision_prompt_is_targeted_with_length_and_kept_criteria(
    make_lesson_runner: MakeLesson,
) -> None:
    c = await make_lesson_runner(verifier=[claims(CLAIM)])
    await c.wait_status("completed")

    second = c.prompt_of_writer(2)
    assert "1500 mots" in second and "2500" in second
    assert "Définitions et prérequis (90/100)" in second
    assert "Révise de façon ciblée" in second
    assert "trop longue" not in second


async def test_too_long_previous_version_asks_to_shorten_first(
    make_lesson_runner: MakeLesson,
) -> None:
    long = lesson_markdown(2600, urls=(URLS[0], URLS[1]))
    c = await make_lesson_runner(writer=[long])
    await c.wait_status("completed")

    assert "trop longue" in c.prompt_of_writer(2)
