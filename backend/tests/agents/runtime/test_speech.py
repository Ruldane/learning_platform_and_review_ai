"""Prise de parole du débat (D82) : 150 mots au plus imposés par le code, citations `[n]` d'un
catalogue numéroté, bulle finale qui remplace celle des tokens."""

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
