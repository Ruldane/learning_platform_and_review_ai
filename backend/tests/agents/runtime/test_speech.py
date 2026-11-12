"""Prise de parole du débat (D82) : 150 mots au plus imposés par le code, citations `[n]` d'un
catalogue numéroté, bulle finale qui remplace celle des tokens."""

import re

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage

from app.agents.runtime.speech import (
    CitationEntry,
    cap_words,
    count_words,
    extract_citations,
    speak,
)
from tests.agents.runtime.runner_helpers import fake_llm


@pytest.mark.parametrize(
    ("text", "limit", "expected"),
    [
        ("Un. Deux trois. Quatre cinq six.", 3, "Un. Deux trois."),
        ("un deux trois quatre", 2, "un deux …"),
        ("court", 150, "court"),
        ("Un deux ! Trois quatre ? cinq six", 5, "Un deux ! Trois quatre ?"),
        ("Fin citée [1]. Suite ici et là.", 4, "Fin citée [1]."),
        ("Le ML aide. [1] Puis la suite qui dépasse.", 4, "Le ML aide. [1]"),
        ("Le ML aide. [1, 2] Puis la suite qui dépasse.", 4, "Le ML aide. [1, 2]"),
        ("Le ML aide. » [3] Puis la suite qui dépasse.", 4, "Le ML aide. » [3]"),
        ("Une ligne.\n\nDeux lignes ici. Trois.", 5, "Une ligne.\n\nDeux lignes ici."),
        ("Phrase « entre guillemets. » puis la suite qui dépasse.", 4,
         "Phrase « entre guillemets. »"),
    ],
)  # fmt: skip
def test_cap_words(text: str, limit: int, expected: str) -> None:
    assert cap_words(text, limit) == expected


def test_citation_markers_are_not_words() -> None:
    assert count_words("Selon [1] et [2, 3] : oui.") == 3


def test_cap_words_keeps_text_within_the_limit() -> None:
    long = " ".join(f"mot{n}" for n in range(151))
    capped = cap_words(long, 150)
    assert capped.endswith(" …") and count_words(capped) == 150


_KEEP = re.compile(r"^Objection :", re.MULTILINE)
_LONG = " ".join(f"mot{n}" for n in range(160)) + "."


def test_cap_words_keeps_objection_line() -> None:
    objection = "Objection : dix semaines ne tiennent pas dans ce budget serré."
    text = f"{_LONG}\n{objection}"  # 170 mots, l'objection en dernière ligne
    assert count_words(text) == 170
    capped = cap_words(text, 150, keep=_KEEP)
    assert capped.endswith(f"\n{objection}") and count_words(capped) <= 150
    assert capped.startswith("mot0 mot1") and " …\n" in capped
    assert cap_words(text, 150) == cap_words(text, 150, keep=None)  # sans `keep` : comme avant


def test_cap_words_keep_changes_nothing_when_the_line_survives() -> None:
    text = f"Objection : trop long.\n{_LONG}"
    assert cap_words(text, 150, keep=_KEEP) == cap_words(text, 150) == "Objection : trop long."
    assert cap_words("Court.\nObjection : non.", 150, keep=_KEEP) == "Court.\nObjection : non."


def test_cap_words_keeps_only_the_first_matching_line() -> None:
    text = f"Objection : une.\n{_LONG}\nObjection : deux."
    assert cap_words(text, 150, keep=_KEEP) == "Objection : une."


def test_objection_line_longer_than_the_limit_is_cut() -> None:
    text = "Intro.\nObjection : " + " ".join(["trop"] * 20)
    capped = cap_words(text, 5, keep=_KEEP)
    assert capped == "Objection : trop trop trop trop …"


def test_kept_line_after_a_full_budget_stands_alone() -> None:
    text = "Un deux trois.\nObjection : quatre cinq six."
    assert cap_words(text, 4, keep=_KEEP) == "Objection : quatre cinq six."


def test_extract_citations_keeps_known_markers_in_order() -> None:
    cat = [CitationEntry(1, "A", "https://a.org"), CitationEntry(2, "Mémoire", memory_item_id="m1")]
    found = extract_citations("Voir [2] puis [1], [9] et [2].", cat)
    assert [c.index for c in found] == [2, 1]
    assert (found[0].title, found[0].memory_item_id, found[0].url) == ("Mémoire", "m1", None)
    assert (found[1].title, found[1].url) == ("A", "https://a.org")


def test_marker_after_the_cut_sentence_is_still_cited() -> None:
    cat = [CitationEntry(1, "A")]
    capped = cap_words("Le ML aide. [1] Puis la suite qui dépasse.", 4)
    assert [c.index for c in extract_citations(capped, cat)] == [1]


def test_extract_citations_reads_grouped_markers() -> None:
    cat = [CitationEntry(n, f"S{n}") for n in (1, 2, 3)]
    assert [c.index for c in extract_citations("Ainsi [3, 1] et [2,3].", cat)] == [3, 1, 2]
    assert extract_citations("Rien à citer [x] ni [].", cat) == []


async def _model(replies: list[str]) -> BaseChatModel:
    return await fake_llm(replies).get_chat_model("u1", "rapide", agent="skeptic")


async def test_speak_emits_capped_message_with_citations(
    emitted: list[dict[str, object]],
) -> None:
    words = ["Selon", "[1]", *(f"mot{n}" for n in range(150))]  # 151 mots, sans point
    model = await _model([" ".join(words)])
    cat = [CitationEntry(1, "Source A", "https://a.org"), CitationEntry(2, "B")]
    spoken = await speak(
        model,
        [HumanMessage("Ta position ?")],
        agent="skeptic",
        step="tour-1",
        intent="je formule une objection",
        catalog=cat,
        max_words=150,
    )
    assert spoken.words == 150 and count_words(spoken.text) <= 150
    assert [c.index for c in spoken.citations] == [1]
    kinds = [e["__tremplin_event__"] for e in emitted]
    assert kinds == ["agent.started", "agent.message"]
    started, message = emitted[0], emitted[1]
    assert started["agent"] == message["agent"] == "skeptic"
    assert started["payload"] == {"step": "tour-1", "intent": "je formule une objection"}
    payload = message["payload"]
    assert isinstance(payload, dict) and payload["text"] == spoken.text
    assert payload["citations"] == [
        {"index": 1, "title": "Source A", "url": "https://a.org", "memory_item_id": None}
    ]
    assert payload["message_id"]


async def test_speak_keeps_a_short_reply_whole(emitted: list[dict[str, object]]) -> None:
    model = await _model(["  Je suis d'accord avec la Stratège [2].  "])
    spoken = await speak(
        model,
        [HumanMessage("?")],
        agent="practitioner",
        step="tour-2",
        intent="je réponds",
        catalog=[CitationEntry(2, "B")],
        max_words=150,
    )
    assert spoken.text == "Je suis d'accord avec la Stratège [2]."
    assert spoken.words == 6 and [c.index for c in spoken.citations] == [2]


async def test_speak_asks_once_more_when_revise_objects(emitted: list[dict[str, object]]) -> None:
    provider_model = fake_llm(["Sans nom [1].", "Je réponds au Sceptique [1].", "jamais"])
    model = await provider_model.get_chat_model("u1", "rapide", agent="practitioner")
    seen: list[str] = []

    def revise(text: str) -> str | None:
        seen.append(text)
        return None if "Sceptique" in text else "Nomme un autre agent."

    spoken = await speak(
        model,
        [HumanMessage("?")],
        agent="practitioner",
        step="tour-2",
        intent="je réponds",
        catalog=[CitationEntry(1, "A")],
        max_words=150,
        revise=revise,
    )
    assert seen == ["Sans nom [1]."]  # une seule nouvelle demande, jamais une troisième
    assert spoken.revised and spoken.text == "Je réponds au Sceptique [1]."
    messages = [e for e in emitted if e["__tremplin_event__"] == "agent.message"]
    assert len(messages) == 1  # la bulle est corrigée, pas doublée
    assert messages[0]["payload"]["text"] == spoken.text  # type: ignore[index]


async def test_speak_without_objection_keeps_the_first_reply(
    emitted: list[dict[str, object]],
) -> None:
    model = await _model(["Bonne réponse [1]."])
    spoken = await speak(
        model,
        [HumanMessage("?")],
        agent="skeptic",
        step="tour-2",
        intent="je réponds",
        catalog=[],
        max_words=150,
        revise=lambda text: None,
    )
    assert not spoken.revised and spoken.text == "Bonne réponse [1]."


async def test_speak_keeps_the_matching_line_at_the_cut(emitted: list[dict[str, object]]) -> None:
    model = await _model([f"{_LONG}\nObjection : trop de semaines [1]."])
    spoken = await speak(
        model,
        [HumanMessage("?")],
        agent="skeptic",
        step="tour-1",
        intent="je formule une objection",
        catalog=[CitationEntry(1, "A")],
        max_words=150,
        keep=_KEEP,
    )
    assert spoken.text.endswith("\nObjection : trop de semaines [1].") and spoken.words <= 150
    assert [c.index for c in spoken.citations] == [1]
