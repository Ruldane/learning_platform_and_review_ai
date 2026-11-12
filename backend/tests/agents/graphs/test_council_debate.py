"""Débat du Conseil (D85) : ordre de parole, 150 mots, citations, réponses nommées dès le tour 2,
objection du Sceptique, messages et commandes de January, arrêt anticipé, carte du domaine.
Faux modèles par agent, faux moteurs, vraie base."""

import json
from collections import Counter
from collections.abc import Awaitable, Callable

import pytest

from app.agents.nodes.debate_turn import broken_rules, names_other_debater
from app.agents.runtime.speech import count_words
from tests.agents.graphs.council_models import DEBATERS, SPEECH, STABLE, CouncilModels
from tests.agents.graphs.council_support import Council, MakeCouncil

LONG_TAIL = " " + " ".join(f"mot{n}" for n in range(200))


def round_marker(number: int) -> str:
    return f"Tour en cours : {number}\n"


def once_in_round(c: Council, number: int, action: Callable[[], Awaitable[None]]) -> None:
    """Exécute `action` pendant la première prise de parole du tour `number`."""
    done: list[bool] = []

    async def hook(agent: str, prompt: str) -> None:
        if not done and agent in DEBATERS and round_marker(number) in prompt:
            done.append(True)
            await action()

    c.models.hooks.append(hook)


async def test_four_agents_debate_three_rounds(make_council_runner: MakeCouncil) -> None:
    models = CouncilModels()
    models.when("practitioner", round_marker(2), SPEECH["practitioner"] + LONG_TAIL)
    c = await make_council_runner(models=models, rounds=3)
    await c.to_choice()
    msgs = await c.agent_messages(step_prefix="tour-")
    assert Counter(m.agent for m in msgs) == {a: 3 for a in DEBATERS}
    assert all(len(m.payload["text"].split()) <= 150 for m in msgs)
    assert max(count_words(m.payload["text"]) for m in msgs) <= 150
    positions = await c.agent_messages(step_prefix="positions")
    assert Counter(m.agent for m in positions) == {a: 1 for a in DEBATERS}  # tour 1
    opening = [m.payload["text"] for m in await c.agent_messages() if m.agent == "moderator"]
    assert opening[0].startswith("Tour 1 : Stratège, Praticien, Éclaireur, Sceptique")
    assert sum(text.startswith("Tour ") for text in opening) == 4  # 1 + debate_rounds
    later = c.prompt_of(msgs[-1])
    assert "Praticien, tour 1" in later and SPEECH["practitioner"] in later  # tours précédents


async def test_turn_cites_catalog_entries(make_council_runner: MakeCouncil) -> None:
    c = await make_council_runner()
    await c.to_choice()
    kept = [f for f in await c.source_found() if f["kind"] == "page" and f["verdict"] == "kept"]
    first = (await c.agent_messages(step_prefix="positions"))[0]
    assert first.payload["citations"][0]["index"] == 1
    assert first.payload["citations"][0]["url"] == kept[0]["url"]
    prompt = c.prompt_of(first)
    assert "[1]\n<<<CONTENU_NON_FIABLE" in prompt  # titre et résumé encadrés, numéro hors cadre


async def test_round_two_reply_must_name_another_agent(make_council_runner: MakeCouncil) -> None:
    models = CouncilModels()
    models.when("strategist", round_marker(2), "Il faut un socle solide d'abord [1].")
    c = await make_council_runner(models=models)
    await c.to_choice()
    replies = [m for m in await c.agent_messages(step_prefix="tour-2") if m.agent == "strategist"]
    assert len(replies) == 1  # la bulle est corrigée, pas doublée
    assert replies[0].payload["text"] == SPEECH["strategist"]
    asked = [call for call in models.calls if "ne respecte pas ces règles" in call.prompt]
    assert [call.agent for call in asked] == ["strategist"]
    assert "répondre nommément" in asked[0].prompt or "réponds nommément" in asked[0].prompt


async def test_rule_still_broken_after_one_retry_is_accepted(
    make_council_runner: MakeCouncil,
) -> None:
    models = CouncilModels()
    bare = "Il faut un socle solide d'abord [1]."
    models.when("practitioner", round_marker(2), bare, bare)
    c = await make_council_runner(models=models)
    await c.to_choice()
    replies = [m for m in await c.agent_messages(step_prefix="tour-2") if m.agent == "practitioner"]
    assert [m.payload["text"] for m in replies] == [bare]
    assert sum("ne respecte pas ces règles" in call.prompt for call in models.calls) == 1


async def test_skeptic_raises_an_objection_each_round(make_council_runner: MakeCouncil) -> None:
    models = CouncilModels()
    models.when("skeptic", round_marker(2), "Je rejoins le Stratège et January [1].")
    c = await make_council_runner(models=models, rounds=2)
    await c.to_choice()
    skeptic = [m for m in await c.agent_messages() if m.agent == "skeptic"]
    assert len(skeptic) == 3
    assert all("\nObjection :" in m.payload["text"] for m in skeptic)


async def test_long_skeptic_turn_keeps_its_objection_line(make_council_runner: MakeCouncil) -> None:
    long_turn = "Je réponds au Stratège :" + LONG_TAIL + "\nObjection : trop de notions [1]."
    models = CouncilModels()
    models.when("skeptic", round_marker(2), long_turn)
    c = await make_council_runner(models=models, rounds=2)
    await c.to_choice()
    skeptic = [m for m in await c.agent_messages(step_prefix="tour-2") if m.agent == "skeptic"]
    text = skeptic[0].payload["text"]
    assert text.endswith("\nObjection : trop de notions [1].") and count_words(text) <= 150
    assert sum("ne respecte pas ces règles" in call.prompt for call in models.calls) == 0


@pytest.mark.parametrize(
    "line", ["**Objection :** trop long", "1. Objection : x", "- Objection : x", "Objections : x"]
)
def test_objection_variants_are_accepted(line: str) -> None:
    assert "objection" not in broken_rules(line, agent="skeptic", round=1, answer_january=False)
    assert "objection" in broken_rules(
        line.replace("bjection", "pinion"), agent="skeptic", round=1, answer_january=False
    )


async def test_message_during_round_one_is_answered_by_name_in_round_two(
    make_council_runner: MakeCouncil,
) -> None:
    models = CouncilModels()
    first_of_round_two = "Je réponds au Praticien : un socle d'abord [1]."
    for agent in DEBATERS:
        models.when(agent, round_marker(2) + "Réponds", first_of_round_two)
    c = await make_council_runner(models=models)
    once_in_round(c, 1, lambda: c.post_message("Je préfère les projets pratiques"))
    await c.to_choice()
    first = (await c.agent_messages(step_prefix="tour-2"))[0]
    assert "January" in first.payload["text"] and "projets pratiques" in c.prompt_of(first)
    assert "Tu parles en premier" in c.prompt_of(first)
    positions = await c.agent_messages(step_prefix="positions")
    assert all("projets pratiques" not in c.prompt_of(m) for m in positions)


async def test_shorter_command_caps_turns_at_80_words(make_council_runner: MakeCouncil) -> None:
    models = CouncilModels()
    for agent in DEBATERS:
        models.when(agent, round_marker(2), SPEECH[agent] + LONG_TAIL)
    c = await make_council_runner(models=models, rounds=2)
    once_in_round(c, 1, lambda: c.post_message("", "shorter"))
    await c.to_choice()
    shorter = await c.agent_messages(step_prefix="tour-2")
    assert len(shorter) == 4 and all(count_words(m.payload["text"]) <= 80 for m in shorter)
    assert all("80 mots au maximum" in c.prompt_of(m) for m in shorter)
    after = await c.agent_messages(step_prefix="tour-3")  # l'angle vaut pour un tour
    assert all("150 mots au maximum" in c.prompt_of(m) for m in after)


async def test_to_proposals_command_skips_remaining_rounds(
    make_council_runner: MakeCouncil,
) -> None:
    c = await make_council_runner(rounds=3)
    once_in_round(c, 2, lambda: c.post_message("", "to_proposals"))
    await c.to_choice()
    assert len(await c.agent_messages(step_prefix="tour-2")) == 1  # l'orateur en cours finit
    assert await c.agent_messages(step_prefix="tour-3") == []
    assert not any("Fais le point du tour." in p for p in c.prompts())
    assert len(await c.events("proposal.ready")) == 2


async def test_another_round_command_adds_a_round(make_council_runner: MakeCouncil) -> None:
    c = await make_council_runner(rounds=1)
    once_in_round(c, 1, lambda: c.post_message("", "another_round"))
    await c.to_choice()
    assert len(await c.agent_messages(step_prefix="tour-3")) == 4


async def test_moderator_stops_early_when_positions_are_stable(
    make_council_runner: MakeCouncil,
) -> None:
    models = CouncilModels()
    models.when("moderator", "Fais le point du tour.", STABLE)
    c = await make_council_runner(models=models, rounds=3)
    await c.to_choice()
    assert len(await c.agent_messages(step_prefix="tour-2")) == 4
    assert await c.agent_messages(step_prefix="tour-3") == []
    summaries = [m for m in await c.agent_messages(step_prefix="bilan-") if m.agent == "moderator"]
    assert [m.payload["text"] for m in summaries] == ["Les positions ne bougent plus."]


async def test_scribe_draws_domain_map_after_round_one(make_council_runner: MakeCouncil) -> None:
    c = await make_council_runner()
    await c.to_choice()
    b = await c.events("board.update")
    assert b[0]["kind"] == "domain_map" and b[0]["board_id"] and b[0]["step"] == 1
    assert [x["kind"] for x in b] == [
        "domain_map",
        "prerequisites",
        "timeline",
        "timeline",
        "comparison",
    ]
    assert [x["step"] for x in b] == [1, 2, 3, 4, 5]
    assert len(c.store.boards) == 5 and len(c.store.attached) == 2  # une frise par proposition
    domain_prompt = next(p.prompt for p in c.models.calls if "carte du domaine" in p.prompt)
    assert "Stratège, tour 1" in domain_prompt


async def test_scribe_publishes_and_saves_only_the_normalized_mermaid(
    make_council_runner: MakeCouncil,
) -> None:
    models = CouncilModels()
    raw = 'flowchart LR\nA["x < y"] -->|suite| B(List<String>)'
    board = json.dumps({"title": "Carte", "mermaid": raw})
    models.when("scribe", "dessiner la carte du domaine", board)
    c = await make_council_runner(models=models)
    await c.to_choice()
    domain = next(x for x in await c.events("board.update") if x["kind"] == "domain_map")
    expected = 'flowchart LR\n  n1["x #lt; y"] -->|"suite"| n2("List#lt;String#gt;")'
    assert domain["mermaid"] == expected
    assert c.store.board_codes[(c.sid, domain["step"])] == expected


async def test_invalid_board_twice_is_skipped_without_failing(
    make_council_runner: MakeCouncil,
) -> None:
    models = CouncilModels()
    bad = '{"title": "Carte", "mermaid": "flowchart TD\\nA-->B\\nclick A \\"https://x\\""}'
    models.when("scribe", "dessiner la carte du domaine", bad, bad)
    c = await make_council_runner(models=models)
    await c.to_choice()
    kinds = [x["kind"] for x in await c.events("board.update")]
    assert "domain_map" not in kinds and kinds[0] == "prerequisites"
    assert sum("Schéma refusé" in call.prompt for call in models.calls) == 1


def test_names_other_debater() -> None:
    assert names_other_debater("Je réponds au Stratège.", "skeptic")
    assert names_other_debater("L'Eclaireur a raison.", "skeptic")
    assert not names_other_debater("Je suis sceptique.", "practitioner")  # l'adjectif
    assert not names_other_debater("Le Sceptique que je suis insiste.", "skeptic")  # soi-même


async def test_scout_debates_with_the_practitioners_it_spotted(
    make_council_runner: MakeCouncil,
) -> None:
    c = await make_council_runner()
    await c.to_choice()
    scout = next(m for m in await c.agent_messages(step_prefix="positions") if m.agent == "scout")
    prompt = c.prompt_of(scout)
    line = prompt.index("- Ada Lovelace — Ingénieure IA")
    assert prompt.rfind("<<<CONTENU_NON_FIABLE", 0, line) > prompt.rfind("<<<FIN_", 0, line)
    others = [m for m in await c.agent_messages(step_prefix="positions") if m.agent != "scout"]
    assert all("Ada Lovelace" not in c.prompt_of(m) for m in others)


async def test_board_invalid_once_cleaned_is_asked_again(make_council_runner: MakeCouncil) -> None:
    """Revue finale de la phase 4, M1 : un titre trop court une fois nettoyé n'interrompt pas le
    Conseil (pas de `ValidationError`) ; il compte comme un refus, et le Scribe redessine."""
    models = CouncilModels()
    short = json.dumps({"title": "  ab ", "mermaid": 'flowchart TD\nA["Bases"] --> B["Projet"]'})
    fenced = json.dumps({"title": "Carte", "mermaid": "```\nA-->B\n```"})
    models.when("scribe", "dessiner la carte du domaine", short, fenced)
    c = await make_council_runner(models=models)
    await c.to_choice()
    kinds = [x["kind"] for x in await c.events("board.update")]
    assert "domain_map" not in kinds and kinds[0] == "prerequisites"
    assert sum("Schéma refusé" in call.prompt for call in models.calls) == 1
