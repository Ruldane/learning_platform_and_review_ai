"""Les changements du comité relus par le code (D147, D155) : un nom propre que le profil ne dit
pas (employeur, école) est signalé « à vérifier », jamais gardé comme conseil ; les mots de section
d'un CV (« Compétences », « Formation »…) ne sont pas des noms."""

import pytest

from app.agents.tools.committee_schema import ChangeDraft, committee_changes
from tests.support.text_claims import COMPANY, P


def one(text: str, allowed: list[str] | None = None):  # type: ignore[no-untyped-def]
    [change] = committee_changes(
        [ChangeDraft(text=text, persona="recruiter", fact_ids=[])], P, allowed or []
    )
    return change


def test_absent_employer_is_flagged_to_check() -> None:
    change = one("Mets en avant ton expérience chez Capgemini dans la section Expériences.")
    assert change.needs_skill and change.terms == ["Capgemini"]
    assert change.text.startswith("À vérifier : ton profil ne dit pas Capgemini.")
    assert "Ne l'écris pas dans ton CV" in change.text and "Mets en avant" not in change.text


def test_absent_school_is_flagged_to_check() -> None:
    change = one("Ajoute ton diplôme de l'École Polytechnique en tête de la section Formation.")
    assert change.needs_skill and "Polytechnique" in " ".join(change.terms)
    assert change.text.startswith("À vérifier : ton profil ne dit pas")
    assert "Ajoute" not in change.text


@pytest.mark.parametrize(
    "text",
    [
        "Place la section Compétences avant la section Expériences.",
        "Remonte la Formation et les Projets en haut du CV.",
        "Mets le Résumé en tête de la section Profil.",
        "Move the Skills section above Experience and Education.",
    ],
)
def test_section_words_are_not_names(text: str) -> None:
    change = one(text)
    assert not change.needs_skill and change.terms == [] and change.text == text


def test_company_of_the_posting_and_profile_names_stay_free() -> None:
    change = one(f"Mets en avant ton expérience chez {COMPANY}.", [COMPANY])
    assert not change.needs_skill
    assert not one("Mets en avant Python et Docker dans la section Compétences.").needs_skill


def test_skill_terms_keep_the_acquire_template() -> None:
    change = one("Ajoute Kubernetes chez Capgemini dans la section Compétences.")
    assert change.text.startswith("À acquérir : Kubernetes.")
    assert change.needs_skill and change.terms == ["Kubernetes"]
