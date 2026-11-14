"""Contrôles du brouillon du profil maître par le code (D124) : nombres canonisés
(`cv_lexicon.numbers_in`), lignes au chiffre introuvable, sources posées par le code, faits
introuvables retirés (sauf note)."""

import pytest

from app.agents.tools.cv_lexicon import numbers_in
from app.agents.tools.cv_schema import MasterProfileData, assign_fact_ids
from app.agents.tools.profile_check import (
    appears,
    blank_facts,
    plain,
    removed_facts,
    tag_sources,
    unsupported_lines,
    without_lines,
)
from app.agents.tools.profile_port import ProfileSource
from tests.support.profile import CV_TEXT, LINKEDIN_TEXT, NOTE, profile

CV = ProfileSource("cv", CV_TEXT)
LINKEDIN = ProfileSource("linkedin", LINKEDIN_TEXT)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Réduit de 30 % le temps", {"30%"}),
        ("30% de plus", {"30%"}),
        ("1 000 factures", {"1000"}),
        ("1 000 factures", {"1000"}),
        ("1000 factures", {"1000"}),
        ("un budget de 12 k€", {"12000"}),
        ("un budget de 12 000 €", {"12000"}),
        ("1,5 M€ de chiffre", {"1500000"}),
        ("2,50 points", {"2.5"}),
        ("un fichier de 5 Mo en 12 km", {"5", "12"}),
        ("x1a2 et v2 ne comptent pas", set()),
        ("près d'un tiers", set()),
    ],
)
def test_numbers_are_canonical(text: str, expected: set[str]) -> None:
    assert numbers_in(text) == expected


def test_plain_and_appears_use_whole_words() -> None:
    assert plain("Développeuse IA — Atelier Fictif") == "developpeuse ia atelier fictif"
    assert plain("C++ et C#") == "c++ et c#"
    hay = plain(CV_TEXT)
    assert appears("SQL", hay) and not appears("SQ", hay) and not appears("C", hay)
    assert appears("développeuse ia", hay)
    long = "Développeuse Python et IA forte de cinq ans d'expérience en données et en agents"
    assert appears(long, hay)  # 80 % des mots, reformulé
    assert not appears("Experte Kubernetes, AWS et Terraform depuis dix ans au moins", hay)


def numbered(**over: object) -> MasterProfileData:
    return assign_fact_ids(blank_facts(profile(**over)))


def test_unsupported_lines_need_a_number_from_a_source() -> None:
    draft = numbered()
    draft.experiences[0].achievements[0].text = "Réduit de 45 % les coûts"
    draft.experiences[1].achievements[0].text = "Automatisé le contrôle de 12000 factures par mois"
    assert unsupported_lines(draft, [CV]) == ["x1a1"]
    assert unsupported_lines(draft, [CV, ProfileSource("note", "45 %")]) == []
    kept = without_lines(draft, ["x1a1"])
    assert [x.id for x in kept.experiences[0].achievements] == ["x1a2"]


def test_blank_facts_clears_model_ids_and_sources() -> None:
    clean = blank_facts(profile())
    assert clean.title is not None and (clean.title.id, clean.title.sources) == ("", [])
    assert all(x.id == "" and x.sources == [] for x in clean.experiences)
    assert all(a.id == "" for x in clean.experiences for a in x.achievements)
    assert all(s.sources == [] for s in clean.skills)


def test_tag_sources_sets_documents_title_and_summary() -> None:
    draft = numbered(skills=[{"name": "Python"}, {"name": "Qdrant"}])
    tagged = tag_sources(draft, [CV, LINKEDIN])
    assert tagged.title is not None and tagged.title.sources == ["cv"]
    assert tagged.summary is not None and tagged.summary.sources == ["cv"]
    assert [x.sources for x in tagged.experiences] == [["cv", "linkedin"], ["cv"]]
    assert {s.name: s.sources for s in tagged.skills} == {
        "Python": ["cv", "linkedin"],
        "Qdrant": ["linkedin"],
    }
    assert tagged.education[0].sources == ["cv"] and tagged.languages[0].sources == ["cv"]


def test_link_matches_without_scheme() -> None:
    links = [{"label": "GitHub", "url": "https://www.github.com/camille-exemple"}]
    draft = numbered(links=links)
    cv = ProfileSource("cv", f"{CV_TEXT}\ngithub.com/camille-exemple")
    assert tag_sources(draft, [cv]).links[0].sources == ["cv"]
    assert tag_sources(draft, [CV]).links == []


def test_untraced_fact_goes_to_note_or_is_removed() -> None:
    draft = numbered(
        skills=[{"name": "Python"}, {"name": "Kubernetes"}],
        title={"text": "Architecte cloud"},
    )
    tagged = tag_sources(draft, [CV])
    assert [s.name for s in tagged.skills] == ["Python"] and tagged.title is None
    assert removed_facts(draft, tagged) == ["Architecte cloud", "Kubernetes"]
    with_note = tag_sources(draft, [CV, ProfileSource("note", NOTE)])
    assert {s.name: s.sources for s in with_note.skills} == {
        "Python": ["cv"],
        "Kubernetes": ["note"],
    }


def test_removed_experience_is_reported_once_with_its_lines() -> None:
    draft = numbered()
    draft.experiences[1].company = "Société Inventée"
    tagged = tag_sources(draft, [CV])
    assert len(tagged.experiences) == 1
    assert removed_facts(draft, tagged) == ["Développeuse Python — Société Inventée"]
