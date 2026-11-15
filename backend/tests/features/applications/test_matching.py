"""Doublons des candidatures (7.1)."""

from datetime import date, timedelta

from app.db.models.applications import ApplicationStatus
from app.features.applications.service.matching import Hit, Incoming, alert_message, match
from app.features.applications.service.rules import ApplicationView
from app.features.postings.service.rules import company_key, posting_url_key

TODAY = date(2026, 11, 15)


def incoming(
    *,
    url: str | None = None,
    company: str = "Société Fictive",
    title: str = "Développeuse IA",
    posting_id: str | None = None,
    possible: frozenset[str] = frozenset(),
    distinct: frozenset[str] = frozenset(),
) -> Incoming:
    return Incoming(
        url_norm=posting_url_key(url) if url else None,
        company_norm=company_key(company),
        title=title,
        posting_id=posting_id,
        possible_posting_ids=possible,
        distinct_from=distinct,
    )


def app(
    app_id: str,
    *,
    url: str | None = None,
    company: str = "Société Fictive",
    title: str = "Développeuse IA",
    status: ApplicationStatus = "applied",
    applied: date | None = date(2026, 11, 3),
    created: date = date(2026, 11, 1),
    posting_id: str | None = None,
    distinct: frozenset[str] = frozenset(),
) -> ApplicationView:
    return ApplicationView(
        id=app_id,
        status=status,
        company_norm=company_key(company),
        title=title,
        url_norm=posting_url_key(url) if url else None,
        posting_id=posting_id,
        applied_on=applied,
        interview_on=None,
        answered_on=None,
        created_on=created,
        distinct_from=distinct,
    )


def test_url_with_tracking_is_certain() -> None:
    existing = app("a1", url="https://www.exemple.org/jobs/42?utm_source=x", title="Autre titre")
    hits = match(incoming(url="https://exemple.org/jobs/42/#postuler"), [existing], TODAY)
    assert hits == [Hit("certain", "a1")]


def test_title_similarity_probable() -> None:
    hits = match(incoming(title="Développeuse IA (H/F)"), [app("a1")], TODAY)
    assert hits == [Hit("probable", "a1")]


def test_possible_needs_same_company_and_a_listed_posting() -> None:
    near = app("a1", title="Ingénieure données", applied=date(2026, 6, 1), posting_id="p9")
    other_company = app("a2", company="Autre SA", title="Ingénieure données", posting_id="p9")
    hits = match(incoming(possible=frozenset({"p9"})), [near, other_company], TODAY)
    assert hits == [Hit("possible", "a1")]


def test_other_title_same_company_within_30_days_is_info() -> None:
    other = "Chef de projet"
    recent = app("a1", title=other, applied=TODAY - timedelta(days=29))
    old = app("a2", title=other, applied=TODAY - timedelta(days=31))
    assert match(incoming(), [recent], TODAY) == [Hit("info", "a1")]
    assert match(incoming(), [old], TODAY) == []
    draft = app("a3", title=other, status="to_apply", applied=None, created=TODAY - timedelta(5))
    assert match(incoming(), [draft], TODAY) == [Hit("info", "a3")]


def test_other_company_is_silent() -> None:
    assert match(incoming(), [app("a1", company="Autre SA")], TODAY) == []


def test_distinct_pair_is_silent() -> None:
    existing = app("a1", posting_id="p1", distinct=frozenset({"p2"}))
    assert match(incoming(posting_id="p2"), [existing], TODAY) == []
    # L'autre sens : l'offre entrante a déjà confirmé la fiche (ou son offre) comme autre poste.
    assert match(incoming(distinct=frozenset({"a1"})), [app("a1")], TODAY) == []
    assert match(incoming(distinct=frozenset({"p1"})), [app("a1", posting_id="p1")], TODAY) == []
    assert match(incoming(posting_id="p3"), [app("a1")], TODAY) == [Hit("probable", "a1")]


def test_same_posting_is_not_a_duplicate() -> None:
    assert match(incoming(posting_id="p1"), [app("a1", posting_id="p1")], TODAY) == []


def test_one_level_per_application_the_strongest() -> None:
    url = "https://exemple.org/jobs/42"
    existing = app("a1", url=url)  # même lien, même entreprise, même titre
    assert match(incoming(url=url), [existing], TODAY) == [Hit("certain", "a1")]


def test_hits_are_sorted_by_level_then_recent_first() -> None:
    url = "https://exemple.org/jobs/1"
    apps = [
        app("info-new", title="Chef de projet", applied=date(2026, 11, 10)),
        app("probable-old", applied=date(2026, 10, 1)),
        app("probable-new", applied=date(2026, 11, 2)),
        app("certain", url=url, title="Autre"),
        app("info-old", title="Designer", applied=date(2026, 10, 25)),
    ]
    hits = match(incoming(url=url), apps, TODAY)
    assert [h.application_id for h in hits] == [
        "certain",
        "probable-new",
        "probable-old",
        "info-new",
        "info-old",
    ]


def test_alert_message_wording() -> None:
    day = date(2026, 11, 3)
    assert alert_message(
        "certain", "Société Fictive", "Développeuse IA", "applied", day, TODAY
    ) == (
        "Attention, tu as déjà postulé chez Société Fictive pour le poste Développeuse IA"
        " le 3 novembre (statut : Postulée)."
    )
    assert alert_message("probable", "Exemple Tech", "Data", "to_apply", day, TODAY) == (
        "Attention, tu as déjà une fiche chez Exemple Tech pour le poste Data,"
        " créée le 3 novembre (statut : À postuler)."
    )
    assert "le 3 novembre 2025 (statut : Refus)" in alert_message(
        "certain", "Autre SA", "Data", "rejected", date(2025, 11, 3), TODAY
    )
    assert "le 1er décembre" in alert_message(
        "certain", "Autre SA", "Data", "applied", date(2026, 12, 1), TODAY
    )


def test_info_message_wording() -> None:
    past = TODAY - timedelta(days=12)
    assert alert_message("info", "Société Fictive", "Chef de projet", "applied", past, TODAY) == (
        "Pour info : tu as postulé chez Société Fictive il y a 12 jours, pour le poste"
        " Chef de projet."
    )
    one = alert_message("info", "Autre SA", "Data", "applied", TODAY - timedelta(days=1), TODAY)
    assert "il y a 1 jour," in one
    draft = alert_message("info", "Autre SA", "Data", "to_apply", TODAY - timedelta(days=4), TODAY)
    assert draft == "Pour info : tu as une fiche chez Autre SA il y a 4 jours, pour le poste Data."
