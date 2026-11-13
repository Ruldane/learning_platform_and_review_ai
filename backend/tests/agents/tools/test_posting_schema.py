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
        "level": "confirme",
        "language": "fr",
    }
    return PostingAnalysis(**(fields | kwargs))


def test_keyword_must_appear_verbatim() -> None:
    problems = keyword_problems(analysis(keywords=[kw("Kubernetes")]), "… Python …")
    assert problems == [
        "Le mot clé « Kubernetes » ne figure pas tel quel dans l'offre : "
        "recopie-le exactement comme il est écrit, ou retire-le."
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
