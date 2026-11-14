"""Validateur des modifications (6.12, revue) : ordres de grandeur en lettres, verbes de proportion,
termes ambigus du lexique (« vue », « spring », « rest »…) qui ne sont un outil que sous leur forme
de produit."""

import pytest

from app.agents.tools.cv_validator import NUMBER, RATIO, TOOL, validate
from tests.support.cv_review import A, analysis, profile, rewrite


@pytest.mark.parametrize(
    "after",
    [
        "Une trentaine de clients",
        "Une vingtaine de clients",
        "Une quarantaine de clients",
        "Une cinquantaine de clients",
        "Une soixantaine de clients",
        "Une quinzaine de clients",
        "Une centaine de clients",
        "Un millier de clients",
        "Zéro incident, 32 clients",
        "Dozens of clients",
        "Hundreds of clients",
        "Thousands of clients",
    ],
)
def test_approximate_number_words_are_figures(after: str) -> None:
    v = validate(rewrite("x1a1", after), profile(line="32 clients"), A)
    assert v.status == "to_confirm"
    assert v.blocks[0] == NUMBER


def test_an_approximation_the_fact_already_makes_is_ok() -> None:
    v = validate(
        rewrite("x1a1", "Une trentaine de clients"), profile(line="Une trentaine de clients"), A
    )
    assert v.status == "ok"


@pytest.mark.parametrize(
    "after",
    [
        "Traffic doubled",
        "Traffic tripled",
        "Traffic halved",
        "Traffic twice as high",
        "Tenfold increase",
        "Trafic décuplé",
        "Trafic doublé",
        "Trafic triplé",
        "Coûts divisés par deux",
        "Coûts réduits, moitié moins",
        "Traffic x10",
        "Traffic quadrupled",
    ],
)
def test_ratio_verbs_and_english_forms_need_a_number_in_facts(after: str) -> None:
    v = validate(rewrite("x1a1", after), profile(line="Réalisation"), A)
    assert v.status == "to_confirm"
    assert RATIO in v.blocks


@pytest.mark.parametrize(
    "after",
    [
        "Vue d'ensemble des indicateurs",
        "Données préparées en vue de l'analyse",
        "Livraison plus vite",
        "Point de vue métier",
        "Tableaux de bord de pilotage",
        "Mise au point de rest en cuisine",
        "Le reste du budget",
    ],
)
def test_ambiguous_words_are_not_tools_in_common_use(after: str) -> None:
    assert validate(rewrite("x1a1", after), profile(line="Réalisation"), A).status == "ok"


@pytest.mark.parametrize(
    "after",
    [
        "Interface en Vue",
        "Interface en vue.js",
        "Interface en Vue 3",
        "Services en Spring",
        "Services en spring boot",
        "Services REST API",
        "Base de données Oracle",
        "Applications en Swift",
        "Entrepôt sur Hive",
        "Prototypes sous Sketch",
        "Jeux sous Unity",
        "Build avec Vite",
    ],
)
def test_ambiguous_terms_in_product_form_are_tools(after: str) -> None:
    v = validate(rewrite("x1a1", after), profile(line="Réalisation"), A)
    assert v.status == "to_confirm"
    assert TOOL in v.blocks


def test_ambiguous_term_named_by_the_posting_still_goes_to_gap() -> None:
    v = validate(
        rewrite("x1a1", "Interface en vue"), profile(line="Réalisation"), analysis(keywords=["Vue"])
    )
    assert (v.status, v.gap_terms) == ("to_gap", ["Vue"])


def test_ambiguous_term_in_the_skills_is_ok() -> None:
    v = validate(rewrite("x1a1", "Interface en Vue"), profile(skills=["Vue"]), A)
    assert v.status == "ok"


@pytest.mark.parametrize(
    "after",
    [
        "Interfaces développées en react",
        "Migration du front vers angular",
        "Automatisation via des scripts bash",
        "Reporting sous excel",
        "Traitements batch en spark",
        "Jobs spark quotidiens",
        "Déploiement sur des postes windows",
        "Alertes envoyées sur slack",
        "Déploiements via helm",
        "Tests avec jest",
        "Tests avec mocha",
        "Tests avec cypress",
        "Intégration avec sap",
        "Scripts en ruby",
        "Services en scala",
        "API en flask",
        "Application en dart",
    ],
)
def test_real_tools_in_lowercase_are_flagged_again(after: str) -> None:
    """Un outil qui n'a que sa lecture d'outil n'est pas un terme ambigu (revue 6.12)."""
    v = validate(rewrite("x1a1", after), profile(line="Réalisation"), A)
    assert v.status == "to_confirm"
    assert TOOL in v.blocks


@pytest.mark.parametrize(
    "word", ["react", "angular", "bash", "excel", "spark", "windows", "slack", "helm", "sap"]
)
def test_removed_tools_start_a_sentence_flagged_too(word: str) -> None:
    v = validate(
        rewrite("x1a1", f"{word.capitalize()} pour le reporting interne"),
        profile(line="Réalisation"),
        A,
    )
    assert TOOL in v.blocks
