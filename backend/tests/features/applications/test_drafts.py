"""Brouillons de relance (SPEC 6.2, D140) : gabarits fixes, aucun appel LLM, aucun fait inventé :
seuls l'entreprise, le poste, les dates et le prénom du contact y figurent."""

from datetime import date

import pytest

from app.agents.tools.kit_schema import split_followups
from app.db.models.applications import ReminderKind
from app.features.applications.service.drafts import (
    draft_for,
    kit_followup,
    linkedin_search_url,
)
from app.features.applications.service.kit_items import words_of

APPLIED = date(2026, 11, 8)
INTERVIEW = date(2026, 11, 14)
KINDS: tuple[ReminderKind, ...] = ("linkedin_7", "email_14", "close_21", "thanks", "news_7")


def draft(kind: ReminderKind, **over: object) -> str:
    values: dict[str, object] = {
        "language": "fr",
        "company": "Société Fictive",
        "title": "Développeuse IA",
        "contact_name": None,
        "applied_on": APPLIED,
        "interview_on": INTERVIEW,
        "kit_followup": None,
    }
    return draft_for(kind, **{**values, **over})  # type: ignore[arg-type]


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_every_template_names_company_and_title(kind: ReminderKind, language: str) -> None:
    text = draft(kind, language=language)
    assert "Société Fictive" in text and "Développeuse IA" in text
    assert "{" not in text and "None" not in text


def test_french_dates_in_full_and_contact_first_name() -> None:
    text = draft("linkedin_7", contact_name="Julie Martin")
    assert text.startswith("Bonjour Julie,")
    assert "8 novembre 2026" in text and "Martin" not in text
    assert "14 novembre 2026" in draft("thanks")
    assert "14 novembre 2026" in draft("news_7")


def test_english_template_and_dates() -> None:
    text = draft("linkedin_7", language="en", contact_name="Julie Martin")
    assert text.startswith("Hello Julie,") and "November 8, 2026" in text
    assert "Bonjour" not in text
    assert draft("email_14", language="en").startswith("Subject:")
    assert draft("email_14").startswith("Objet :")


def test_missing_dates_are_left_out_not_invented() -> None:
    text = draft("linkedin_7", applied_on=None)
    assert "novembre" not in text and "le None" not in text
    assert "novembre" not in draft("thanks", interview_on=None)


def test_close_21_is_a_proposal_to_classify() -> None:
    text = draft("close_21")
    assert "Sans réponse" in text and "Société Fictive" in text


def test_kit_text_replaces_the_template_for_both_followups() -> None:
    assert draft("linkedin_7", kit_followup="Texte du kit") == "Texte du kit"
    assert draft("email_14", kit_followup="Texte du kit") == "Texte du kit"
    assert draft("thanks", kit_followup="Texte du kit") != "Texte du kit"
    assert draft("close_21", kit_followup="Texte du kit") != "Texte du kit"


def test_kit_followup_splits_the_two_emails() -> None:
    content = "Premier mail.\n\n---\n\nSecond mail."
    assert kit_followup(content, "linkedin_7") == "Premier mail."
    assert kit_followup(content, "email_14") == "Second mail."
    assert kit_followup("Un seul.", "email_14") is None
    assert kit_followup(content, "thanks") is None
    assert kit_followup("", "linkedin_7") is None


def test_linkedin_search_url_is_encoded() -> None:
    url = linkedin_search_url("Société Fictive", "Développeuse IA & Data")
    assert url.startswith("https://www.linkedin.com/search/results/people/?keywords=")
    assert " " not in url and "&Data" not in url and "%26" in url
    assert "Soci%C3%A9t%C3%A9%20Fictive" in url


@pytest.mark.parametrize(
    "content",
    [
        "Premier mail.\n---\nSecond mail.",
        "Premier mail.\n\n---\n\nSecond mail.",
        "Premier mail.\n  ---  \nSecond mail.",
        "Premier mail.\n-----\nSecond mail.",
        "Premier mail.\r\n---\r\nSecond mail.",
    ],
)
def test_followups_split_same_rule_graph_and_route(content: str) -> None:
    """M3 : une seule découpe, celle du graphe (comptes de mots), du fil et des brouillons de
    relance ; une ligne de tirets seule sépare, des tirets collés à du texte non."""
    assert split_followups(content) == ("Premier mail.", "Second mail.")
    assert kit_followup(content, "linkedin_7") == "Premier mail."
    assert kit_followup(content, "email_14") == "Second mail."
    assert words_of("followups", content) == {"day_7": 2, "day_14": 2}


def test_followups_split_keeps_dashes_glued_to_text() -> None:
    glued = "Premier --- mail.\n---\nSecond mail."
    assert split_followups(glued) == ("Premier --- mail.", "Second mail.")
    assert split_followups("Un seul.") == ("Un seul.", "")
