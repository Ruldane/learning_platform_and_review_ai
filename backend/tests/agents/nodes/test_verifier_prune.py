"""Périmètre du Vérificateur et retrait déterministe des phrases non sourcées (D97 n° 11), rejoués
sur le cas réel anonymisé de la fin de phase 4. Pur, sans réseau ni modèle."""

from app.agents.nodes.verifier import check_lesson, in_scope, prune
from tests.support.lessons import SOURCES, TITLE
from tests.support.verifier_case import (
    C_ABSENT,
    C_APPS,
    C_GIT,
    C_NAME,
    C_OBJECTIVE,
    C_PIP,
    C_PREREQUISITE,
    C_TERMINAL,
    CODE,
    OBJECTIVE,
    real_case_lesson,
)

LESSON = real_case_lesson()


def test_real_case_lesson_passes_the_deterministic_checks() -> None:
    assert check_lesson(LESSON, title=TITLE, sources=SOURCES).problems == []


def test_objective_and_prerequisite_claims_are_out_of_scope() -> None:
    claims = [C_OBJECTIVE, C_APPS, C_PREREQUISITE, C_TERMINAL, C_PIP]
    assert in_scope(LESSON, claims) == [C_APPS, C_TERMINAL, C_PIP]


def test_a_claim_that_cannot_be_located_stays_in_scope() -> None:
    assert in_scope(LESSON, [C_ABSENT, "Affirmation sans aucune citation."]) == [
        C_ABSENT,
        "Affirmation sans aucune citation.",
    ]


def test_prune_removes_only_the_sentence_carrying_the_claim() -> None:
    result = prune(LESSON, [C_APPS])
    assert (result.removed, result.unlocated) == (1, 0)
    assert "construire des applications" not in result.markdown
    assert "Pour le métier visé par Alice" in result.markdown  # la phrase suivante reste
    assert OBJECTIVE in result.markdown
    assert check_lesson(result.markdown, title=TITLE, sources=SOURCES).problems == []


def test_prune_handles_several_claims_of_the_real_case() -> None:
    result = prune(LESSON, [C_APPS, C_NAME, C_GIT])
    assert (result.removed, result.unlocated) == (3, 0)
    assert "Python est un langage polyvalent" not in result.markdown
    assert "s'intègre le plus naturellement" not in result.markdown
    assert "VS Code est aujourd'hui l'outil le plus complet pour Python [2]." in result.markdown
    assert "### Choisir son éditeur Python" in result.markdown
    assert check_lesson(result.markdown, title=TITLE, sources=SOURCES).problems == []


def test_prune_never_touches_code_blocks_nor_the_rest_of_a_paragraph() -> None:
    result = prune(LESSON, [C_TERMINAL])
    assert result.removed == 1
    assert CODE in result.markdown  # le même texte dans un bloc de code reste
    assert "**Étape 4 — Exécuter.** Vous devez voir deux passages s'afficher." in result.markdown


def test_prune_removes_a_whole_list_item_when_it_is_the_claim() -> None:
    claim = "« sans commits, impossible de revenir en arrière » : aucune source ne le dit."
    result = prune(LESSON, [claim])
    assert result.removed == 1 and "Ignorer le versionnage" not in result.markdown
    assert "- **Confondre `python` et `python3`**" in result.markdown


def test_removing_an_essential_line_breaks_the_count_check() -> None:
    result = prune(LESSON, [C_PIP])
    assert result.removed == 1 and "pip" not in result.markdown
    problems = check_lesson(result.markdown, title=TITLE, sources=SOURCES).problems
    assert any("L'essentiel en 5 lignes" in p for p in problems)


def test_fragments_are_matched_without_case_spacing_nor_punctuation() -> None:
    claim = "“PYTHON EST un   langage polyvalent, qui sert aussi bien” : non sourcé."
    assert prune(LESSON, [claim]).removed == 1
    quoted = "« c’est aussi là que Git s’intègre le plus naturellement » : non sourcé."
    assert prune(LESSON, [quoted]).removed == 1  # apostrophe typographique, gras dans la leçon


def test_unlocated_claims_are_counted_and_nothing_is_removed_for_them() -> None:
    result = prune(LESSON, [C_APPS, C_ABSENT, "« Python est » : trop court pour être localisé."])
    assert (result.removed, result.unlocated) == (1, 2)


def test_headings_are_never_matched() -> None:
    result = prune(LESSON, ["« Choisir son éditeur Python » : titre."])
    assert (result.removed, result.unlocated) == (0, 1) and result.markdown == LESSON
