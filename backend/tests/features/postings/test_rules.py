"""Règles pures des offres (6.2) : clé de lien, clé d'entreprise, titres proches, texte, ATS."""

import pytest

from app.core.errors import AppError
from app.features.postings.service.rules import (
    MIN_POSTING_CHARS,
    company_key,
    detect_ats,
    enough_text,
    posting_url_key,
    title_similarity,
)


@pytest.mark.parametrize(
    "a,b",
    [
        ("https://www.Exemple.org/jobs/42/?utm_source=x", "https://exemple.org/jobs/42"),
        ("https://exemple.org/j?b=2&a=1", "https://exemple.org/j?a=1&b=2"),
        (
            "https://exemple.org/j?id=7&gclid=g&utm_campaign=c&ref=r#postuler",
            "https://exemple.org/j?id=7",
        ),
    ],
)
def test_posting_url_key(a: str, b: str) -> None:
    assert posting_url_key(a) == posting_url_key(b)


@pytest.mark.parametrize(
    "url",
    [
        "https://www.exemple.org/jobs/42/?utm_source=x&q=d%C3%A9v+ia&b=",
        "HTTPS://Exemple.org:8443/",
        "https://exemple.org/offre?ref=1",
    ],
)
def test_posting_url_key_is_idempotent(url: str) -> None:
    key = posting_url_key(url)
    assert posting_url_key(key) == key


def test_posting_url_key_keeps_real_parameters_and_scheme() -> None:
    assert posting_url_key("https://exemple.org/j?reference=1&id=2") == (
        "https://exemple.org/j?id=2&reference=1"
    )
    assert posting_url_key("http://exemple.org/j") != posting_url_key("https://exemple.org/j")


@pytest.mark.parametrize("url", ["ftp://exemple.org/a", "exemple.org/jobs", "https://"])
def test_posting_url_key_refuses_invalid_links(url: str) -> None:
    with pytest.raises(AppError):
        posting_url_key(url)


def test_company_key_drops_legal_suffix() -> None:
    assert company_key("Société Fictive SAS") == company_key("societe fictive")
    assert company_key("Société Fictive S.A.S.") == "societe fictive"
    assert company_key("Exemple GmbH & Co") == "exemple gmbh co"
    assert company_key("SAS") == "sas"


def test_title_similarity() -> None:
    assert title_similarity("AI Product Engineer", "Product Engineer AI") >= 0.85
    assert title_similarity("AI Product Engineer", "Comptable") < 0.85
    assert title_similarity("", "Comptable") == 0.0


def test_enough_text() -> None:
    long_word = "x" * MIN_POSTING_CHARS
    assert enough_text("mot " * 49 + long_word)  # 50 mots
    assert not enough_text("mot " * 48 + long_word)  # 49 mots, assez long
    assert not enough_text("mot " * 60)  # 60 mots, 239 caractères
    assert not enough_text("   ")


def test_detect_ats() -> None:
    assert detect_ats(["https://job-boards.greenhouse.io/x/jobs/1"]) == "Greenhouse"
    assert detect_ats(["https://exemple.org/a", "https://jobs.lever.co/exemple/1"]) == "Lever"
    assert detect_ats(["https://exemple.wd3.myworkdayjobs.com/fr"]) == "Workday"
    assert detect_ats(["https://notgreenhouse.io/x", "pas un lien", "http://[::1"]) is None
    assert detect_ats([]) is None
