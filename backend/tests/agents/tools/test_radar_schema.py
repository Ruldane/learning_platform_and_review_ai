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

FR_GENERIC = [
    "offre d'emploi {r}{w}",
    "{r}{w} recrutement CDI",
    "{r} H/F{w}",
    "{r}{w} emploi",
    "{r} offre{w}",
    "{r}{w} poste à pourvoir",
    "{r}{w} on recrute",
    "{r}{w} postuler",
]
EN_GENERIC = ["{r} job{w}", "{r}{w} hiring", "{r}{w} careers", "{r}{w} apply"]


def _expected(templates: list[str], role: str, zone: str) -> list[str]:
    return [t.format(r=role, w=f" {zone}") for t in templates]


def test_queries_built_by_code() -> None:
    queries = radar_queries("Ingénieur IA", "Lyon", ("fr",))
    assert queries == [
        *_expected(FR_GENERIC, "Ingénieur IA", "Lyon"),
        *[f"Ingénieur IA Lyon site:{hint}" for hint in SITE_HINTS],
    ]
    # Les requêtes générales d'abord (SearXNG répond mal aux `site:`), les ciblées en dernier.
    assert len(queries) == radar_schema.MAX_QUERIES == 12
    assert all("site:" in q for q in queries[8:]) and not any("site:" in q for q in queries[:8])


def test_queries_by_language_capped_and_without_duplicates() -> None:
    both = radar_queries("Data Engineer", "Paris", ("fr", "en"))
    fr = _expected(FR_GENERIC, "Data Engineer", "Paris")
    en = _expected(EN_GENERIC, "Data Engineer", "Paris")
    # Les langues alternent (le plafond n'en prive aucune), puis deux requêtes ciblées au moins.
    assert both[:8] == [q for pair in zip(fr[:4], en, strict=True) for q in pair]
    assert both[8:10] == fr[4:6]
    assert len(both) == 12 and both[10:] == [
        f"Data Engineer Paris site:{h}" for h in SITE_HINTS[:2]
    ]
    assert radar_queries("Data Engineer", "Paris", ("en", "en")) == [
        *en,
        *[f"Data Engineer Paris site:{hint}" for hint in SITE_HINTS],
    ]
    assert len(set(both)) == len(both)


def test_queries_carry_only_role_and_zone() -> None:
    """Aucune donnée inventée : les mots des requêtes sont le poste, la zone, des mots fixes et
    des sites publics."""
    fixed = {"offre", "d'emploi", "recrutement", "CDI", "job", "Data", "Engineer", "Paris", "H/F"}
    fixed |= {"emploi", "poste", "à", "pourvoir", "on", "recrute", "postuler", "hiring"}
    fixed |= {"careers", "apply"}
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
    assert radar_schema.MAX_QUERIES <= 12  # le plafond de requêtes d'une session
    assert radar_schema.READ_BATCH * 6 == rules.MAX_READS
    assert radar_schema.BATCH * 10 == rules.MAX_RUN
