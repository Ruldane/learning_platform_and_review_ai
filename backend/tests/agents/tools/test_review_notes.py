"""Rapport de revue : aucune garantie de passage de l'ATS ni d'acceptation, assurée par le code
(revue 6.13 m6), pas seulement par le prompt."""

import pytest

from app.agents.nodes.review_save import report_of
from app.agents.tools.review_notes import promises, without_promises
from tests.support.cv_review import A


@pytest.mark.parametrize(
    "sentence",
    [
        "Ce CV passera l'ATS sans problème.",
        "Le passage de l'ATS est garanti.",
        "Ton CV est garanti de passer le filtre.",
        "Tu seras retenue à coup sûr.",
        "Le CV sera accepté par le filtre.",
        "Cette version va passer tous les filtres.",
        "Ce CV obtient 100 % de réussite à l'ATS.",
        "This CV will pass the ATS.",
        "Acceptance is guaranteed.",
    ],
)
def test_a_promise_is_found(sentence: str) -> None:
    assert promises(sentence)


@pytest.mark.parametrize(
    "sentence",
    [
        "Aucune garantie de passage de l'ATS.",
        "Le passage de l'ATS n'est pas garanti.",
        "Cette revue ne garantit pas le passage de l'ATS.",
        "No guarantee that the ATS will like it.",
        "100 % des mots clés obligatoires sont couverts.",
        "Sections usuelles : bien lues.",
        "Peu de LangGraph.",
    ],
)
def test_an_honest_sentence_is_kept(sentence: str) -> None:
    assert not promises(sentence)


def test_only_the_promising_sentence_is_removed_and_an_emptied_note_goes() -> None:
    notes = [
        "Intitulés usuels. Ce CV passera l'ATS à coup sûr.",
        "Garanti : il sera accepté.",
        "Aucune garantie de passage.",
    ]
    assert without_promises(notes) == ["Intitulés usuels.", "Aucune garantie de passage."]


def test_the_report_never_carries_a_promise() -> None:
    state = {
        "ats_notes": ["Le CV passera l'ATS.", "Sections usuelles : bien lues."],
        "strengths": ["Résultat chiffré. Succès garanti."],
        "risks": ["Il sera rejeté sans aucun doute.", "Peu de LangGraph."],
    }
    report = report_of(state, A)  # type: ignore[arg-type]
    assert report.ats_notes == ["Sections usuelles : bien lues."]
    assert report.strengths == ["Résultat chiffré."]
    assert report.risks == ["Peu de LangGraph."]
