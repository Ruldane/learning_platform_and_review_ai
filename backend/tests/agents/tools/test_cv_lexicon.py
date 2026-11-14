"""Lexique du CV (6.12) : chiffres sous toutes leurs écritures, proportions, mots de titre."""

import pytest

from app.agents.tools.cv_lexicon import (
    NUMBER_WORDS,
    RATIO_NUMBERS,
    RATIO_WORDS,
    TECH_TERMS,
    TITLE_WORDS,
    clean_text,
    figures_in,
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
