"""Validateur des modifications (6.12, critère 18.3) : aucun fait absent du profil n'entre dans le
CV. Chiffres sous toutes leurs écritures, proportions, outils (casse, compétences, offre)."""

import pytest

from app.agents.tools.cv_schema import (
    Experience,
    Identity,
    Line,
    MasterProfileData,
    assign_fact_ids,
)
from app.agents.tools.cv_validator import GAP, NUMBER, RATIO, TOOL, validate
from app.agents.tools.posting_schema import Keyword, PostingAnalysis
from tests.support.cv_review import A, add, analysis, profile, rewrite

# --- chiffres ---


@pytest.mark.parametrize(
    ("fact", "after"),
    [
        ("1000 h gagnées", "Réduit les délais de 1 000 h"),
        ("1 000 h gagnées", "Réduit les délais de 1000 h"),
        ("Coûts réduits de 30 %", "Coûts réduits de 30%"),
        ("Coûts réduits de 30%", "Coûts réduits de 30 %"),
        ("Note de 1,5 sur 5", "Note de 1.5 sur 5"),
        ("Budget de 12 k€", "Budget de 12 000 €"),
        ("Coûts réduits de 30 %", "Coûts réduits de 30 %"),
        ("Coûts réduits de 30 %", "Coûts réduits de ３０ ％"),
        ("Coûts réduits de 30 %", "Coûts réduits de 30 pour cent"),
        ("Équipe de cinq personnes", "Équipe de 5 personnes"),
        ("Équipe de 5 personnes", "Équipe de cinq personnes"),
    ],
)
def test_number_formats_match(fact: str, after: str) -> None:
    assert validate(rewrite("x1a1", after), profile(line=fact), A).status == "ok"


@pytest.mark.parametrize(
    ("fact", "after"),
    [
        ("Coûts réduits de 30 %", "Coûts réduits de 45 %"),  # chiffre inventé
        (
            "Coûts réduits de 30 %",
            "Coûts réduits de 30 personnes",
        ),  # un pourcentage n'est pas un nombre
        ("Coûts réduits", "Coûts réduits de trente pour cent"),  # chiffre en lettres
        ("Coûts réduits", "Coûts réduits de 30​%"),  # espace de largeur nulle
        ("Équipe de 5 personnes", "Équipe de 15 personnes"),
        ("Équipe de 5 personnes", "Équipe de plusieurs dizaines de personnes"),
        ("Coûts réduits", "Plus de cent clients accompagnés"),
    ],
)
def test_absent_number_needs_confirmation(fact: str, after: str) -> None:
    v = validate(rewrite("x1a1", after), profile(line=fact), A)
    assert v.status == "to_confirm"
    assert v.blocks[0] == NUMBER


def test_number_of_another_uncited_fact_does_not_count() -> None:
    p = assign_fact_ids(
        MasterProfileData(
            identity=Identity(name="Camille Exemple"),
            experiences=[
                Experience(
                    role="AI Engineer",
                    company="Société Fictive",
                    achievements=[Line(text="Coûts réduits de 30 %"), Line(text="Équipe animée")],
                    sources=["cv"],
                )
            ],
        )
    )
    assert validate(rewrite("x1a2", "Équipe animée, coûts réduits de 30 %"), p, A).status == (
        "to_confirm"
    )
    cited = rewrite("x1a2", "Équipe animée, coûts réduits de 30 %", fact_ids=["x1a1"])
    assert validate(cited, p, A).status == "ok"


# --- proportions ---


def test_ratio_word_needs_a_number_in_facts() -> None:
    v = validate(
        rewrite("x1a1", "Près d'un tiers de coûts en moins"), profile(line="Coûts réduits"), A
    )
    assert v.status == "to_confirm"
    assert "Proportion" in v.blocks[0]
    assert v.blocks == [RATIO]


def test_ratio_word_backed_by_its_family_number() -> None:
    v = validate(
        rewrite("x1a1", "Coûts réduits de moitié, soit 50 %"),
        profile(line="Coûts réduits de 50 %"),
        A,
    )
    assert v.status == "ok"


def test_ratio_word_already_in_facts_is_ok() -> None:
    v = validate(
        rewrite("x1a1", "Coûts réduits de moitié"), profile(line="Coûts réduits de moitié"), A
    )
    assert v.status == "ok"


def test_a_third_is_not_thirty_percent() -> None:
    v = validate(
        rewrite("x1a1", "Près d'un tiers de coûts en moins"),
        profile(line="Coûts réduits de 30 %"),
        A,
    )
    assert v.status == "to_confirm"
    assert RATIO in v.blocks


@pytest.mark.parametrize(
    "after", ["Trafic x2", "Trafic ×2", "Trafic 2x", "Trafic doublé", "Trafic: double"]
)
def test_multiplier_without_facts_needs_confirmation(after: str) -> None:
    v = validate(rewrite("x1a1", after), profile(line="Trafic augmenté"), A)
    assert v.status == "to_confirm"
    assert RATIO in v.blocks


# --- outils ---


@pytest.mark.parametrize(
    "after",
    ["Déploiement sur kubernetes", "Déploiement sur KUBERNETES", "Déploiement sur Kuber​netes"],
)
def test_tool_case_insensitive_absent_blocks(after: str) -> None:
    v = validate(rewrite("x1a1", after), profile(skills=["Docker"]), A)
    assert v.status == "to_confirm"
    assert TOOL in v.blocks


def test_tool_in_profile_skills_is_ok() -> None:
    v = validate(rewrite("x1a1", "Déploiement sur docker"), profile(skills=["Docker"]), A)
    assert v.status == "ok"


def test_tool_in_cited_fact_is_ok() -> None:
    v = validate(rewrite("x1a1", "Déploiement sur Docker"), profile(line="Déploie sur Docker"), A)
    assert v.status == "ok"


def test_multiword_and_symbol_tools() -> None:
    for after in ("Pipelines CI/CD", "Services en C++", "Données sur Node.js"):
        assert validate(rewrite("x1a1", after), profile(), A).status == "to_confirm"


def test_posting_keyword_not_in_profile_goes_to_gap() -> None:
    v = validate(add("c9", "AWS"), profile(skills=["Docker"]), analysis(keywords=["AWS"]))
    assert v.status == "to_gap"
    assert v.gap_terms == ["AWS"]


def test_rewrite_adding_a_posting_tool_goes_to_gap_not_into_the_cv() -> None:
    """Un outil de l'offre absent du profil : jamais « à confirmer » (cela l'ouvrirait au clic)."""
    posting = analysis(tools=["Terraform"])
    v = validate(
        rewrite("x1a1", "Infrastructure décrite avec terraform"),
        profile(skills=["Docker"]),
        posting,
    )
    assert v.status == "to_gap"
    assert v.gap_terms == ["Terraform"]


def test_posting_term_outside_the_lexicon_goes_to_gap() -> None:
    v = validate(
        rewrite("x1a1", "Pilote la gestion de la dette technique"),
        profile(line="Pilote l'équipe"),
        analysis(keywords=["dette technique"]),
    )
    assert (v.status, v.gap_terms) == ("to_gap", ["dette technique"])


def test_posting_keyword_variant_reports_the_keyword() -> None:
    posting = PostingAnalysis(
        is_job_posting=True,
        title="Data Scientist",
        level="confirme",
        language="fr",
        keywords=[Keyword(term="AWS", variants=["Amazon Web Services"])],
    )
    v = validate(rewrite("x1a1", "Hébergé sur Amazon Web Services"), profile(), posting)
    assert (v.status, v.gap_terms) == ("to_gap", ["AWS"])


def test_posting_keyword_in_profile_is_ok() -> None:
    v = validate(
        rewrite("x1a1", "Modèles en Python"),
        profile(skills=["Python"]),
        analysis(keywords=["Python"]),
    )
    assert v.status == "ok"


def test_gap_wins_over_confirm_and_keeps_every_reason() -> None:
    v = validate(
        rewrite("x1a1", "Déploie sur kubernetes et AWS, coûts -45 %"),
        profile(),
        analysis(keywords=["AWS"]),
    )
    assert v.status == "to_gap"
    assert v.gap_terms == ["AWS"]
    assert {NUMBER, TOOL, GAP} <= set(v.blocks)
