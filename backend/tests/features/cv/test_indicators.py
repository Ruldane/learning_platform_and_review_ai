"""Couverture des exigences obligatoires (6.2, SPEC 5.3)."""

from app.agents.tools.cv_schema import CvLine
from app.agents.tools.posting_schema import Keyword, Requirement
from app.features.cv.service.indicators import Coverage, coverage, requirement_words

PYTHON = Requirement(text="Maîtrise de Python", required=True, skills=["Python"])
ML = Requirement(text="Expérience en Machine Learning", required=True, skills=[])
DOCKER = Requirement(text="Conteneurs", required=True, skills=["Docker"])
NICE = Requirement(text="Connaissance de Rust", required=False, skills=["Rust"])
KEYWORDS = [Keyword(term="Machine Learning", variants=["ML", "apprentissage automatique"])]


def test_coverage_counts_only_fact_backed_lines() -> None:
    lines = [
        CvLine(text="Pipelines Python en production", fact_ids=["x1a1"]),
        CvLine(text="Déploiement Docker", fact_ids=[]),  # ligne sans fait : ne compte pas
        CvLine(text="Projet Rust", fact_ids=["p1"]),
    ]
    assert coverage([PYTHON, ML, DOCKER, NICE], KEYWORDS, lines) == Coverage(
        covered=1,
        total=3,
        percent=33,
        missing=["Expérience en Machine Learning", "Conteneurs"],
    )
    # CV d'origine : toutes ses lignes comptent.
    original = coverage([PYTHON, ML, DOCKER, NICE], KEYWORDS, lines, backed_only=False)
    assert (original.covered, original.percent, original.missing) == (
        2,
        67,
        ["Expérience en Machine Learning"],
    )


def test_coverage_ignores_case_accents_plural() -> None:
    lines = [
        CvLine(text="Modèles d'APPRENTISSAGES AUTOMATIQUES déployés", fact_ids=["x1a1"]),
        CvLine(text="PYTHONS", fact_ids=["c1"]),
        CvLine(text="dockerisation", fact_ids=["c2"]),  # pas le mot entier
    ]
    result = coverage([PYTHON, ML, DOCKER], KEYWORDS, lines)
    assert (result.covered, result.missing) == (2, ["Conteneurs"])


def test_requirement_words_take_overlapping_keywords() -> None:
    keywords = [*KEYWORDS, Keyword(term="Kubernetes"), Keyword(term="Python", variants=["Py"])]
    assert requirement_words(ML, keywords) == [
        "Machine Learning",
        "ML",
        "apprentissage automatique",
    ]
    assert requirement_words(PYTHON, keywords) == ["Python", "Py"]


def test_coverage_without_required_requirement_is_full() -> None:
    assert coverage([NICE], KEYWORDS, []) == Coverage(covered=0, total=0, percent=100, missing=[])
