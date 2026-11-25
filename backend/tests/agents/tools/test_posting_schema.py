"""Analyse d'une offre (6.2) : mots clés présents tels quels, normalisation unique des termes."""

from typing import Any

import pytest
from pydantic import ValidationError

from app.agents.tools.posting_schema import (
    Keyword,
    PostingAnalysis,
    contains_term,
    keyword_problems,
    normalize_term,
)

TEXT = "Nous cherchons une personne qui maîtrise Python et le Machine Learning (scikit-learn), C++."


def kw(term: str) -> Keyword:
    return Keyword(term=term)


def analysis(**kwargs: Any) -> PostingAnalysis:
    fields: dict[str, Any] = {
        "is_job_posting": True,
        "title": "AI Product Engineer",
        "level": "mid_level",
        "language": "fr",
    }
    return PostingAnalysis(**(fields | kwargs))


@pytest.mark.parametrize(("old", "new"), [("confirme", "mid_level"), ("inconnu", "unknown")])
def test_legacy_checkpoint_levels_read_as_english_codes(old: str, new: str) -> None:
    assert analysis(level=old).model_dump(mode="json")["level"] == new


def test_keyword_must_appear_verbatim() -> None:
    problems = keyword_problems(analysis(keywords=[kw("Kubernetes")]), "… Python …")
    assert problems == [
        "The keyword “Kubernetes” does not appear as is in the posting: "
        "copy it exactly as it is written, or remove it."
    ]


def test_keyword_ignores_case_spaces_and_accents() -> None:
    keywords = [
        kw("machine   learning"),
        kw("PYTHON"),
        kw("Maitrise"),
        kw("C++"),
        kw("scikit-learn"),
    ]
    assert keyword_problems(analysis(keywords=keywords), TEXT) == []


def test_keyword_matches_whole_words_only() -> None:
    assert keyword_problems(analysis(keywords=[kw("Pyth")]), TEXT)
    assert keyword_problems(analysis(keywords=[kw("Ma")]), TEXT)


def test_normalize_term() -> None:
    assert normalize_term("  Données   Clés, Node.js_C#  ") == "donnees cles node js c#"
    assert normalize_term("Modèles de langages", plural=True) == "modele de langage"
    assert normalize_term("AWS process", plural=True) == "aws process"
    assert not contains_term("Python", "—")


@pytest.mark.parametrize(
    "bad",
    [{"language": "FR"}, {"title": "x"}, {"keywords": [{"term": "k" * 81}]}, {"tools": ["t" * 81]}],
)
def test_analysis_bounds(bad: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        analysis(**bad)
