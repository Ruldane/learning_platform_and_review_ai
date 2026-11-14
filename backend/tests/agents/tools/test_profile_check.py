"""Contrôles du brouillon du profil maître par le code (D124) : nombres canonisés
(`cv_lexicon.numbers_in`), lignes au chiffre introuvable (titre, résumé et description de projet
compris), sources posées par le code, nombres et noms gardés par un texte reformulé, faits
introuvables retirés (la note ne compte que si elle les porte)."""

import pytest

from app.agents.tools.cv_lexicon import numbers_in
from app.agents.tools.cv_schema import MasterProfileData, assign_fact_ids
from app.agents.tools.profile_check import (
    Hay,
    appears,
    blank_facts,
    named_terms,
    plain,
    removed_facts,
    tag_sources,
    unsupported_lines,
    untraced_lines,
    without_lines,
)
from app.agents.tools.profile_port import ProfileSource
from tests.support.profile import CV_TEXT, LINKEDIN_TEXT, NOTE, profile, profile_data

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
    hay = Hay.of(CV)
    assert appears("SQL", hay) and not appears("SQ", hay) and not appears("C", hay)
    assert appears("développeuse ia", hay)
    long = "Développeuse Python et IA forte de cinq ans d'expérience en données et en agents"
    assert appears(long, hay)  # 80 % des mots, reformulé
    assert not appears("Experte Kubernetes, AWS et Terraform depuis dix ans au moins", hay)


def test_named_terms_are_acronyms_names_and_tools() -> None:
    text = "Développeuse IA. Déployé sur AWS S3 avec Python, puis Kubernetes ; Écrit 3 tests."
    assert named_terms(text) == {"ia", "aws", "s3", "python", "kubernetes"}


SUMMARY = profile_data()["summary"]["text"]


@pytest.mark.parametrize(
    "summary",
    [
        SUMMARY.replace("cinq ans", "15 ans"),  # mot de deux lettres : hors des 80 %
        SUMMARY.replace("utiles.", "utiles, Kubernetes."),  # outil ajouté
        SUMMARY.replace("en données", "en données chez AWS"),  # sigle ajouté
    ],
)
def test_reworded_text_keeps_every_number_and_name(summary: str) -> None:
    assert appears(SUMMARY.replace("Aime", "Elle aime"), Hay.of(CV))  # reformulé : passe
    assert not appears(summary, Hay.of(CV))
    tagged = tag_sources(numbered(summary={"text": summary}), [CV, LINKEDIN])
    assert tagged.summary is None


def test_numbers_of_title_summary_and_description_are_checked() -> None:
    draft = numbered(
        title={"text": "Développeuse IA, 15 ans d'expérience"},
        summary={"text": SUMMARY.replace("cinq ans", "15 ans")},
        projects=[
            {"name": "Assistant interne", "description": "Augmenté de 40 % les conversions"},
            {"name": "Tests", "description": "Couvert 12000 factures"},
        ],
    )
    assert unsupported_lines(draft, [CV]) == ["t1", "s1", "p1"]
    kept = without_lines(draft, ["t1", "s1", "p1"])
    assert kept.title is None and kept.summary is None
    assert [p.description for p in kept.projects] == ["", "Couvert 12000 factures"]


def test_tool_invented_in_a_project_description_drops_the_project() -> None:
    cv = ProfileSource("cv", f"{CV_TEXT}\nAssistant interne : un agent pour le support")
    real = {"name": "Assistant interne", "description": "Un agent pour le support, avec LangGraph"}
    fake = {"name": "Assistant interne", "description": "Un agent déployé sur Kubernetes"}
    assert tag_sources(numbered(projects=[real]), [cv]).projects[0].sources == ["cv"]
    assert tag_sources(numbered(projects=[fake]), [cv]).projects == []


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


def test_untraced_lines_without_a_number_are_found_and_dropped() -> None:
    draft = numbered()
    draft.experiences[0].achievements[0].text = "Migré la production vers Kubernetes"  # inventé
    draft.experiences[1].achievements[0].text = "Fait quelque chose d'inventé sans chiffre"
    assert untraced_lines(draft, [CV]) == ["x1a1", "x2a1"]
    assert (
        unsupported_lines(draft, [CV]) == []
    )  # aucun nombre : l'ancien contrôle ne les voyait pas
    assert untraced_lines(
        draft, [CV, ProfileSource("note", "Migré la production vers Kubernetes")]
    ) == ["x2a1"]
    kept = without_lines(draft, untraced_lines(draft, [CV]))
    assert [x.id for e in kept.experiences for x in e.achievements] == ["x1a2"]


def test_real_lines_of_the_cv_are_never_untraced() -> None:
    assert untraced_lines(numbered(), [CV]) == []
    assert untraced_lines(numbered(), []) != []  # sans document, rien n'est établi


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


def test_untraced_fact_is_removed_unless_the_note_says_it() -> None:
    draft = numbered(
        skills=[{"name": "Python"}, {"name": "Kubernetes"}],
        title={"text": "Architecte cloud"},
        projects=[{"name": "Atelier interne sur les agents"}],
    )
    tagged = tag_sources(draft, [CV])
    assert [s.name for s in tagged.skills] == ["Python"] and tagged.title is None
    assert removed_facts(draft, tagged) == [
        "Architecte cloud",
        "Kubernetes",
        "Atelier interne sur les agents",
    ]
    with_note = tag_sources(draft, [CV, ProfileSource("note", NOTE)])
    assert {s.name: s.sources for s in with_note.skills} == {"Python": ["cv"]}  # note muette
    assert with_note.title is None
    assert [p.sources for p in with_note.projects] == [["note"]]  # la note le dit
    assert removed_facts(draft, with_note) == ["Architecte cloud", "Kubernetes"]


def test_removed_experience_is_reported_once_with_its_lines() -> None:
    draft = numbered()
    draft.experiences[1].company = "Société Inventée"
    tagged = tag_sources(draft, [CV])
    assert len(tagged.experiences) == 1
    assert removed_facts(draft, tagged) == ["Développeuse Python — Société Inventée"]


def _hay(text: str) -> Hay:
    return Hay.of(ProfileSource("cv", text))


@pytest.mark.parametrize(
    ("text", "name"),
    [
        ("C'est un CV d'ingénieure. J'ai travaillé sur 10 Go de logs.", "C"),
        ("C'est un CV d'ingénieure. J'ai travaillé sur 10 Go de logs.", "Go"),
        ("Compétences : C++ et C#", "C"),
        ("Voici le plan : go to market, puis c'est fini", "Go"),
        ("Stockage de 500 Go et 2 To", "Go"),
        ("Rédigé avec soin, j'ai suivi.", "AI"),
        ("Ingénieur R&D chez Société Fictive", "R"),
        ("Rôle de C-level advisor", "C"),
        ("Stratégie Go-to-market", "Go"),
    ],
)
def test_a_short_skill_is_not_found_in_an_elision_a_unit_or_a_longer_name(
    text: str, name: str
) -> None:
    assert not appears(name, _hay(text))


@pytest.mark.parametrize(
    ("text", "name"),
    [
        ("Compétences : Python, C, SQL", "C"),
        ("Langages : Python, Go et Rust", "Go"),
        ("Langages\nGo\nPython", "Go"),
        ("Compétences : C++ et C#", "C++"),
        ("Compétences : C++ et C#", "C#"),
        ("Statistiques avec R.", "R"),
    ],
)
def test_a_short_skill_written_as_a_skill_is_found(text: str, name: str) -> None:
    assert appears(name, _hay(text))
