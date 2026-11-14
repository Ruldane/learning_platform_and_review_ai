"""Lexique du CV (6.12) : chiffres sous toutes leurs écritures, proportions, mots de titre."""

import pytest

from app.agents.tools.cv_lexicon import (
    AMBIGUOUS_TERMS,
    NUMBER_WORDS,
    RATIO_NUMBERS,
    RATIO_WORDS,
    TECH_TERMS,
    TITLE_WORDS,
    clean_text,
    figures_in,
    numbers_in,
    ratio_families,
)


def test_tech_terms_are_lowercase_and_cover_the_usual_names() -> None:
    assert len(TECH_TERMS) >= 150
    assert all(term == term.lower() and term == term.strip() for term in TECH_TERMS)
    expected = {
        "python",
        "aws",
        "kubernetes",
        "langgraph",
        "rag",
        "terraform",
        "scrum",
        "c++",
        "c#",
    }
    assert expected <= TECH_TERMS
    # Les mots de la langue courante ne sont pas des outils.
    assert {"go", "r", "c", "net", "word", "notion", "chef"}.isdisjoint(TECH_TERMS)


def test_every_ratio_family_has_its_numbers_or_is_a_multiplier() -> None:
    assert set(RATIO_WORDS.values()) >= {"half", "third", "quarter", "double", "triple"}
    assert set(RATIO_NUMBERS) <= set(RATIO_WORDS.values())


def test_title_and_number_words() -> None:
    assert {"lead", "senior", "principal", "head", "manager", "directeur", "chef"} <= TITLE_WORDS
    assert "un" not in NUMBER_WORDS
    assert "une" not in NUMBER_WORDS


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("30 %", {"30%"}),
        ("30 %", {"30%"}),
        ("３０ ％", {"30%"}),
        ("30 pour cent", {"30%"}),
        ("trente pour cent", {"30%"}),
        ("thirty percent", {"30%"}),
        ("cent pour cent", {"100%"}),
        ("1 000 h", {"1000"}),
        ("1 000 h", {"1000"}),
        ("1,5 M€", {"1500000"}),
        ("cinq ans", {"5"}),
        ("des dizaines de clients", {"dizaines"}),
        ("3​0 %", {"30%"}),
        ("un projet, une équipe", set()),
    ],
)
def test_figures_in(text: str, expected: set[str]) -> None:
    assert figures_in(text) == expected


def test_clean_text_removes_invisible_characters() -> None:
    assert clean_text("Kuber​netes﻿") == "Kubernetes"


@pytest.mark.parametrize(
    ("text", "families"),
    [
        ("réduit de moitié", {"half"}),
        ("près d'un tiers", {"third"}),
        ("un quart du budget", {"quarter"}),
        ("trafic doublé", {"double"}),
        ("x2", {"double"}),
        ("×3", {"triple"}),
        ("2x", {"double"}),
        ("x10", {"x10"}),
        ("réduit de 30 %", set()),
        ("matrix2 et ax", set()),
    ],
)
def test_ratio_families(text: str, families: set[str]) -> None:
    assert ratio_families(text) == families


@pytest.mark.parametrize(
    "word", ["vingtaine", "trentaine", "quarantaine", "cinquantaine", "soixantaine", "quinzaine"]
)
def test_approximate_number_words(word: str) -> None:
    assert figures_in(f"une {word} de clients") and figures_in(f"une {word} de clients") != {"2"}
    assert figures_in("zéro incident") == {"0"}


def test_ambiguous_terms_are_tech_terms_with_qualifiers() -> None:
    assert {"vue", "vite", "spring", "rest", "swift", "hive", "oracle", "tableau"} <= set(
        AMBIGUOUS_TERMS
    )
    assert set(AMBIGUOUS_TERMS) <= TECH_TERMS


@pytest.mark.parametrize(
    ("text", "families"),
    [
        ("traffic doubled", {"double"}),
        ("twice as fast", {"double"}),
        ("tripled", {"triple"}),
        ("halved", {"half"}),
        ("tenfold", {"x10"}),
        ("décuplé", {"x10"}),
        ("divisé par deux", {"half"}),
        ("divisés par trois", {"third"}),
        ("moitié moins", {"half"}),
    ],
)
def test_ratio_verbs_and_english_forms(text: str, families: set[str]) -> None:
    assert ratio_families(text) == families


def test_ambiguous_terms_are_only_common_words() -> None:
    """Revue 6.12 : un outil qui n'a que sa lecture d'outil reste un outil en minuscules."""
    assert set(AMBIGUOUS_TERMS) == {
        "vue", "vite", "spring", "rest", "swift", "hive", "consul", "sketch", "unity", "unreal",
        "oracle", "tableau", "soap", "vault", "rust", "transformers", "rails",
    }  # fmt: skip


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1,000 stagiaires", {"1000"}),
        ("1.000 stagiaires", {"1000"}),
        ("12.345 lignes", {"12345"}),
        ("1,000,000 de visites", {"1000000"}),
        ("1.000,50 €", {"1000.5"}),
        ("1,000.50 €", {"1000.5"}),
        ("1 stagiaire", {"1"}),
        ("1,5 point", {"1.5"}),
        ("1,50 point", {"1.5"}),
        ("0,125 s", {"0.125"}),
    ],
)
def test_thousands_separators_are_not_decimals(text: str, expected: set[str]) -> None:
    assert numbers_in(text) == expected
