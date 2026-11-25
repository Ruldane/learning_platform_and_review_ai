"""Vérification du dossier de l'entreprise par le code (D142) : le rôle du Vérificateur."""

from datetime import date, timedelta

from app.agents.tools.kit_dossier import UNSOURCED, check_dossier, has_content, render_dossier
from app.agents.tools.kit_schema import CompanyDossier, SourceRef
from tests.agents.graphs.kit_support import dossier_data

TODAY = date(2026, 11, 15)


def make(**over: object) -> CompanyDossier:
    return CompanyDossier.model_validate(dossier_data(**over))


def test_valid_citations_are_kept_and_normalised() -> None:
    checked = check_dossier(make(activity="Édite des logiciels [1,2]."), pages=2, today=TODAY)
    assert checked.dossier.activity == "Édite des logiciels [1, 2]."
    assert (checked.emptied, checked.dropped) == (0, 0)


def test_citation_of_an_unread_page_is_removed() -> None:
    checked = check_dossier(make(activity="Édite des logiciels [1] [5]."), pages=2, today=TODAY)
    assert checked.dossier.activity == "Édite des logiciels [1]."
    only = check_dossier(make(culture="Sobre [3, 1]."), pages=2, today=TODAY)
    assert only.dossier.culture == "Sobre [1]."


def test_text_without_a_read_source_is_emptied() -> None:
    checked = check_dossier(make(product="Aucune source [9].", culture="Sans citation."), 2, TODAY)
    assert checked.dossier.product == "" and checked.dossier.culture == "" and checked.emptied == 2
    assert UNSOURCED in render_dossier("X", checked.dossier, [])


def test_news_must_be_dated_cited_and_under_six_months() -> None:
    def item(text: str, day: date | None) -> dict[str, object]:
        return {"text": text, "date": day.isoformat() if day else None}

    news = [
        item("Récente [1]", TODAY - timedelta(days=100)),
        item("Limite [1]", TODAY - timedelta(days=183)),
        item("Trop ancienne [1]", TODAY - timedelta(days=184)),
        item("Future [1]", TODAY + timedelta(days=1)),
        item("Sans date [1]", None),
        item("Sans source [4]", TODAY),
    ]
    checked = check_dossier(make(news=news), pages=2, today=TODAY)
    assert [n.text for n in checked.dossier.news] == ["Récente [1]", "Limite [1]"]
    assert checked.dropped == 4


def test_questions_keep_their_count_and_lose_invalid_citations() -> None:
    questions = ["Q1 [1] ?", "Q2 [8] ?", "Q3 ?", "Q4 ?", "Q5 ?"]
    checked = check_dossier(make(questions=questions), pages=1, today=TODAY)
    assert checked.dossier.questions == ["Q1 [1] ?", "Q2 ?", "Q3 ?", "Q4 ?", "Q5 ?"]


def test_has_content_needs_one_sourced_thing() -> None:
    empty = make(
        activity="x", product="x", culture="x", interview_process="x",
        stack=[], news=[], watch_points=[],
    )  # fmt: skip
    assert not has_content(check_dossier(empty, 3, TODAY).dossier)
    assert has_content(check_dossier(make(), 3, TODAY).dossier)


def test_render_lists_sources_by_rank() -> None:
    sources = [
        SourceRef(url="https://a.example", title="Page A"),
        SourceRef(url="https://b.example"),
    ]
    text = render_dossier("Société Fictive", make(), sources)
    assert text.startswith("# Company dossier for Société Fictive")
    assert "[1] Page A — https://a.example" in text
    assert "[2] https://b.example — https://b.example" in text
    assert "Estimated size (unsourced) · small or medium-sized business" in text
    assert "## Estimated size" not in text


def test_size_is_omitted_when_unknown() -> None:
    assert "Estimated size" not in render_dossier("X", make(size="unknown"), [])


def test_empty_question_is_not_rendered() -> None:
    checked = check_dossier(make(questions=["Q1 ?", "[8]", "Q3 ?", "Q4 ?", "Q5 ?"]), 1, TODAY)
    text = render_dossier("X", checked.dossier, [])
    assert "1. Q1 ?\n2. Q3 ?\n3. Q4 ?\n4. Q5 ?" in text
    assert "[8]" not in text


def test_news_from_an_old_page_is_dropped_even_with_a_recent_date() -> None:
    day = TODAY.isoformat()
    news = [
        {"text": "Annonce [1]", "date": day},
        {"text": "Annonce bis [2]", "date": day},
        {"text": "Annonce ter [1, 2]", "date": day},
        {"text": "Annonce quater [3]", "date": day},
    ]
    old, recent = TODAY - timedelta(days=184), TODAY - timedelta(days=10)
    checked = check_dossier(make(news=news), 3, TODAY, page_dates=[old, recent, None])
    kept = [n.text for n in checked.dossier.news]
    assert kept == ["Annonce bis [2]", "Annonce ter [1, 2]", "Annonce quater [3]"]
    assert checked.dropped == 1
