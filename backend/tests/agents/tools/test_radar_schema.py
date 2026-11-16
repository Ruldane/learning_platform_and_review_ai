"""Schémas et requêtes du radar (P5, P6) : requêtes construites par le code, extraction bornée, et
accord des règles recopiées côté moteur (il n'importe pas la feature) avec celles de la feature."""

import pytest
from pydantic import ValidationError

from app.agents.tools import radar_port, radar_schema
from app.agents.tools.radar_schema import (
    SITE_HINTS,
    RadarBatch,
    RadarItem,
    SkillNeedLite,
    link_key,
    radar_queries,
    radar_searches,
    salary_in_text,
)
from app.core.errors import AppError
from app.features.postings.service.rules import posting_url_key
from app.features.radar.service import rules


def test_queries_built_by_code() -> None:
    queries = radar_queries("Ingénieur IA", "Lyon", ("fr",))
    assert queries == [
        "offre d'emploi Ingénieur IA Lyon",
        "Ingénieur IA Lyon recrutement CDI",
        *[f"Ingénieur IA Lyon site:{hint}" for hint in SITE_HINTS],
    ]
    assert len(queries) <= 6 and all("site:" in q for q in queries[2:])


def test_queries_by_language_capped_and_without_duplicates() -> None:
    both = radar_queries("Data Engineer", "Paris", ("fr", "en"))
    assert both[:3] == [
        "offre d'emploi Data Engineer Paris",
        "Data Engineer Paris recrutement CDI",
        "Data Engineer job Paris",
    ]
    assert len(both) == 6 and both[3:] == [f"Data Engineer Paris site:{h}" for h in SITE_HINTS[:3]]
    assert radar_queries("Data Engineer", "Paris", ("en", "en")) == [
        "Data Engineer job Paris",
        *[f"Data Engineer Paris site:{hint}" for hint in SITE_HINTS],
    ]
    assert len(set(both)) == len(both)


def test_queries_carry_only_role_and_zone() -> None:
    """Aucune donnée inventée : les mots des requêtes sont le poste, la zone, des mots fixes et
    des sites publics."""
    fixed = {"offre", "d'emploi", "recrutement", "CDI", "job", "Data", "Engineer", "Paris"}
    for query in radar_queries("Data Engineer", "Paris", ("fr", "en")):
        words = [w for w in query.split() if not w.startswith("site:")]
        assert set(words) <= fixed


def test_queries_without_role_or_with_blank_zone() -> None:
    assert radar_queries("  ", "Lyon", ("fr",)) == []
    assert radar_queries("Ingénieur IA", " ", ("fr",))[0] == "offre d'emploi Ingénieur IA"
    assert radar_queries("Ingénieur IA", "Lyon", ())[0] == "offre d'emploi Ingénieur IA Lyon"


def test_searches_carry_a_language() -> None:
    langs = {s.query: s.lang for s in radar_searches("Dev", "Nice", ("fr", "en"))}
    assert langs["offre d'emploi Dev Nice"] == "fr" and langs["Dev job Nice"] == "en"
    assert langs[f"Dev Nice site:{SITE_HINTS[0]}"] == "fr"


def test_item_bounds() -> None:
    ok = {"ref": "p1", "is_job_posting": True, "level": "senior", "tools": ["Docker"]}
    assert RadarItem.model_validate(ok).level == "senior"
    for bad in (
        {**ok, "ref": "p6"},
        {**ok, "level": "expert"},
        {**ok, "title": "x" * 201},
        {**ok, "remote": "x" * 61},
        {**ok, "salary": "x" * 81},
        {**ok, "tools": ["Docker"] * 16},
        {**ok, "skills": [{"name": "Python", "required": True}] * 16},
    ):
        with pytest.raises(ValidationError):
            RadarItem.model_validate(bad)
    with pytest.raises(ValidationError):
        SkillNeedLite(name="x", required=True)
    with pytest.raises(ValidationError):
        RadarBatch(items=[RadarItem(ref="p1", is_job_posting=False)] * 6)


@pytest.mark.parametrize(
    "url",
    [
        "https://www.jobs.example.org/offre/12/?utm_source=x&b=2&a=1#postuler",
        "HTTPS://Jobs.Example.org:443/offre/12",
        "http://jobs.example.org:80/offre/12",
        "https://jobs.example.org:8443/offre/12/",
        "https://jobs.example.org/#/offre/12",
        "https://jobs.example.org/#!/offre/12",
        "https://jobs.example.org/offre?gclid=1&ref=abc",
        "https://[::1]:8080/offre/1",
    ],
)
def test_link_key_matches_posting_url_key(url: str) -> None:
    assert link_key(url) == posting_url_key(url)


@pytest.mark.parametrize(
    "url",
    [
        "ftp://x.org/a",
        "https:///a",
        "https://user:pw@x.org/a",
        "not a link",
        "https://x.org:99999/",
    ],
)
def test_link_key_rejects_what_the_feature_rejects(url: str) -> None:
    with pytest.raises(AppError):
        posting_url_key(url)
    assert link_key(url) is None


@pytest.mark.parametrize(
    ("salary", "text"),
    [
        ("45-55 k€", "Salaire : 45 k€ à 55 k€ brut annuel"),
        ("45 000 - 55 000 €", "De 45 000 € à 55 000 € par an"),
        ("45-55 k€", "Salaire : 450 k€ à 55 k€"),
        ("70 000 €", "Rémunération selon profil"),
        ("selon profil", "Salaire : 45 k€"),
        (None, "Salaire : 45 k€"),
        ("", "45"),
    ],
)
def test_salary_in_text_matches_the_feature(salary: str | None, text: str) -> None:
    assert salary_in_text(salary, text) == rules.salary_shown(salary, text)


def test_bounds_are_the_feature_bounds() -> None:
    assert radar_port.MAX_READS == rules.MAX_READS
    assert radar_port.MAX_CANDIDATES == rules.MAX_CANDIDATES
    assert radar_port.MAX_READABLE == rules.MAX_RUN
    assert radar_schema.MAX_QUERIES * 2 <= 12  # le plafond de requêtes d'une session
    assert radar_schema.READ_BATCH * 6 == rules.MAX_READS
    assert radar_schema.BATCH * 10 == rules.MAX_RUN
