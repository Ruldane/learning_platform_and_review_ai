"""Ids des faits d'une nouvelle version du profil (D124) : un fait inchangé garde son id, un
fait neuf reçoit un numéro jamais pris, la version de January garde ses ids connus."""

from typing import Any

from app.agents.tools.cv_schema import (
    Experience,
    Identity,
    Language,
    Line,
    Link,
    MasterProfileData,
    Project,
    SkillFact,
    assign_fact_ids,
    facts_of,
)
from app.agents.tools.profile_check import blank_facts
from app.features.cv.service.profile_merge import all_ids, keep_known, merge_draft
from tests.support.profile import profile


def first() -> MasterProfileData:
    return assign_fact_ids(blank_facts(profile()))


def test_merge_keeps_ids_of_unchanged_facts() -> None:
    previous = first()
    draft = blank_facts(profile())
    draft.experiences.reverse()  # ordre changé : les ids suivent les faits
    draft.experiences[1].achievements.insert(0, Line(text="Mis en place la revue de code"))
    draft.skills.append(SkillFact(name="Qdrant"))
    draft.skills[0].name = "python"  # même texte normalisé
    merged = merge_draft(draft, previous, all_ids([previous]))
    assert [x.id for x in merged.experiences] == ["x2", "x1"]
    assert [a.id for a in merged.experiences[1].achievements] == ["x1a3", "x1a1", "x1a2"]
    assert merged.skills[0].id == "c1" and merged.skills[-1].id == "c6"
    assert merged.title is not None and merged.title.id == "t1"


def test_freed_numbers_are_never_reused() -> None:
    previous = first()
    older = first()
    older.skills.append(SkillFact(id="c9", name="Ancienne"))
    draft = blank_facts(profile())
    draft.experiences = draft.experiences[1:]  # x1 a disparu
    neuve = draft.experiences[0].model_copy(update={"company": "Neuve"}, deep=True)
    draft.experiences.append(neuve)
    merged = merge_draft(draft, previous, all_ids([previous, older]))
    assert [x.id for x in merged.experiences] == ["x2", "x3"]
    assert [a.id for x in merged.experiences for a in x.achievements] == ["x2a1", "x3a1"]
    draft.skills.append(SkillFact(name="Qdrant"))
    assert merge_draft(draft, previous, all_ids([previous, older])).skills[-1].id == "c10"


def test_merge_without_previous_numbers_from_one() -> None:
    merged = merge_draft(blank_facts(profile()), None, set())
    assert [x.id for x in merged.experiences] == ["x1", "x2"]
    assert merged.experiences[0].achievements[1].id == "x1a2"


def test_keep_known_keeps_assigned_ids_and_marks_january() -> None:
    previous = first()
    edited = previous.model_copy(deep=True)
    edited.experiences[0].role = "Ingénieure IA"  # fait modifié : même id
    edited.skills.append(SkillFact(id="c42", name="Qdrant"))  # id jamais attribué
    edited.skills.append(SkillFact(id="c2", name="Doublon"))  # id déjà porté
    edited.experiences[1].achievements.append(Line(id="x1a1", text="Déplacée"))  # mauvais parent
    kept = keep_known(edited, all_ids([previous]))
    assert kept.experiences[0].id == "x1" and kept.experiences[0].role == "Ingénieure IA"
    assert [s.id for s in kept.skills][-2:] == ["c6", "c7"]
    assert kept.experiences[1].achievements[-1].id == "x2a2"
    assert kept.skills[-2].sources == ["january"]


def _validated_with_january() -> MasterProfileData:
    """v validée : le CV (x1, x2, c1…) plus ce que January a saisi ou confirmé."""
    version = first()
    for fact in (*version.experiences, *version.skills):
        fact.sources = ["cv"]
    version.experiences[0].achievements.append(Line(id="x1a9", text="Encadré une équipe de 8"))
    version.experiences[0].sources = ["cv", "january"]  # fait confirmé en revue
    version.skills.append(SkillFact(id="c40", name="Rust", sources=["january"]))
    version.projects.append(
        Project(id="p7", name="Aurore", description="Assistant", sources=["january"])
    )  # noqa: E501
    version.languages.append(Language(id="l5", name="Italien", level="B1", sources=["january"]))
    version.links.append(
        Link(id="k3", label="Site", url="https://example.org", sources=["january"])
    )  # noqa: E501
    return version


def test_reimport_keeps_the_facts_january_added_with_their_ids() -> None:
    previous = _validated_with_january()
    draft = blank_facts(profile())  # un import qui ne dit rien de tout cela
    merged = merge_draft(draft, previous, all_ids([previous]))
    assert "c40" in [s.id for s in merged.skills] and "Rust" in [s.name for s in merged.skills]
    assert [p.id for p in merged.projects] == ["p7"]
    assert "l5" in [lang.id for lang in merged.languages]
    assert "k3" in [k.id for k in merged.links]
    kept = merged.experiences[0]
    assert kept.id == "x1" and kept.achievements[-1].id == "x1a9"
    assert "january" in kept.sources
    assert len({fid for fid in facts_of(merged)}) == len(facts_of(merged))


def test_reimport_does_not_duplicate_what_the_draft_already_says() -> None:
    previous = _validated_with_january()
    draft = blank_facts(profile())
    draft.skills.append(SkillFact(name="rust"))  # même nom normalisé
    merged = merge_draft(draft, previous, all_ids([previous]))
    assert [s.name.lower() for s in merged.skills].count("rust") == 1
    assert next(s for s in merged.skills if s.name.lower() == "rust").id == "c40"


def test_reimport_carries_a_january_parent_the_draft_dropped() -> None:
    previous = first()
    previous.experiences[1].sources = ["january"]
    draft = blank_facts(profile())
    draft.experiences = draft.experiences[:1]  # x2 a disparu du nouvel import
    merged = merge_draft(draft, previous, all_ids([previous]))
    assert [x.id for x in merged.experiences] == ["x1", "x2"]
    assert merged.experiences[1].achievements[0].id == "x2a1"


def test_a_cv_fact_missing_from_the_draft_is_not_carried() -> None:
    previous = _validated_with_january()
    draft = blank_facts(profile())
    draft.skills = draft.skills[1:]  # c1, venu du CV, n'est plus dans l'import
    merged = merge_draft(draft, previous, all_ids([previous]))
    assert "c1" not in [s.id for s in merged.skills]


def _confirmed_in_review() -> MasterProfileData:
    """v validée : January a confirmé, en revue, « Lead Développeuse » et « Python (expert) »
    (faits du CV réécrits : ids gardés, textes neufs, sources `cv` et `january`)."""
    version = first()
    version.experiences[0].role = "Lead Développeuse"
    version.experiences[0].sources = ["cv", "january"]
    version.skills[0].name = "Python (expert)"
    version.skills[0].sources = ["cv", "january"]
    version.languages[0].level = "C2"  # « Anglais — C2 » confirmé en revue
    version.languages[0].sources = ["cv", "january"]
    version.links.append(
        Link(id="k1", label="GitHub", url="https://github.com/autre", sources=["cv", "january"])
    )
    return version


def test_reimport_does_not_duplicate_a_fact_january_confirmed_in_a_review() -> None:
    previous = _confirmed_in_review()
    company = previous.experiences[0].company
    draft = blank_facts(profile())  # le même CV : « Développeuse » d'origine, « Python »
    draft.experiences[0].role = "Développeuse"
    draft.experiences[0].company = company
    draft.skills[0].name = "Python"
    draft.languages[0].level = None  # le CV ne dit pas le niveau : celui de January reste
    draft.links.append(Link(label="GitHub", url="https://github.com/camille"))
    merged = merge_draft(draft, previous, all_ids([previous]))
    experiences = [x for x in merged.experiences if x.company == company]
    assert [(x.id, x.role) for x in experiences] == [("x1", "Lead Développeuse")]
    texts = [a.text for a in experiences[0].achievements]
    assert len(texts) == len(set(texts))  # les réalisations ne sont pas doublées
    python = [(s.id, s.name) for s in merged.skills if s.name.startswith("Python")]
    assert python == [("c1", "Python (expert)")]
    assert [(lang.id, lang.name, lang.level) for lang in merged.languages] == [
        ("l1", "Anglais", "C2")
    ]
    assert [(k.id, k.url) for k in merged.links] == [("k1", "https://github.com/autre")]
    assert len(set(facts_of(merged))) == len(facts_of(merged))


def test_a_new_achievement_of_the_draft_joins_the_january_experience() -> None:
    previous = _confirmed_in_review()
    draft = blank_facts(profile())
    draft.experiences[0].role = "Développeuse"
    draft.experiences[0].company = previous.experiences[0].company
    draft.experiences[0].achievements.append(Line(text="Nouvelle réalisation du CV"))
    merged = merge_draft(draft, previous, all_ids([previous]))
    kept = next(x for x in merged.experiences if x.id == "x1")
    assert "Nouvelle réalisation du CV" in [a.text for a in kept.achievements]
    ids = [a.id for a in kept.achievements]
    assert len(ids) == len(set(ids)) and "" not in ids


def _bare(**kw: Any) -> MasterProfileData:
    return MasterProfileData(identity=Identity(name="Camille Exemple"), **kw)


def _numbered(data: MasterProfileData) -> MasterProfileData:
    return assign_fact_ids(data)


def _merge(previous: MasterProfileData, draft: MasterProfileData) -> MasterProfileData:
    previous = _numbered(previous)
    return merge_draft(draft, previous, all_ids([previous]))


def test_skills_with_the_same_first_word_are_all_kept() -> None:
    previous = _bare(
        skills=[
            SkillFact(name="Gestion d'équipe", sources=["january"]),
            SkillFact(name="Adobe Illustrator", sources=["january"]),
        ]
    )
    draft = _bare(skills=[SkillFact(name="Gestion de projet"), SkillFact(name="Adobe Photoshop")])
    merged = _merge(previous, draft)
    assert sorted(s.name for s in merged.skills) == [
        "Adobe Illustrator",
        "Adobe Photoshop",
        "Gestion d'équipe",
        "Gestion de projet",
    ]


def test_a_promotion_at_the_same_company_keeps_the_new_cv_fact() -> None:
    previous = _bare(
        experiences=[
            Experience(
                role="Développeuse Python",
                company="Acme",
                start="2020-01",
                sources=["cv", "january"],
            )
        ]
    )
    draft = _bare(
        experiences=[
            Experience(role="Lead Développeuse", company="Acme", start="2019-09", sources=["cv"])
        ]
    )
    merged = _merge(previous, draft)
    assert sorted((x.role, x.start) for x in merged.experiences) == [
        ("Développeuse Python", "2020-01"),
        ("Lead Développeuse", "2019-09"),
    ]


def test_two_jobs_at_one_company_in_another_order_lose_and_duplicate_nothing() -> None:
    previous = _bare(
        experiences=[
            Experience(
                role="Développeuse Python",
                company="Acme",
                achievements=[Line(text="Conçu l'API")],
                sources=["cv", "january"],
            ),
            Experience(
                role="Stagiaire",
                company="Acme",
                achievements=[Line(text="Écrit des tests")],
                sources=["cv"],
            ),
        ]
    )
    draft = _bare(
        experiences=[
            Experience(
                role="Stagiaire développement",
                company="Acme",
                achievements=[Line(text="Écrit des tests")],
            ),
            Experience(
                role="Développeuse", company="Acme", achievements=[Line(text="Conçu l'API")]
            ),
        ]
    )
    merged = _merge(previous, draft)
    assert sorted(x.role for x in merged.experiences) == [
        "Développeuse Python",
        "Stagiaire développement",
    ]
    by_role = {x.role: [a.text for a in x.achievements] for x in merged.experiences}
    assert by_role["Développeuse Python"] == ["Conçu l'API"]
    assert by_role["Stagiaire développement"] == ["Écrit des tests"]


def test_a_confirmed_level_yields_to_another_level_of_the_new_cv() -> None:
    previous = _bare(
        languages=[
            Language(name="Allemand", level=None, sources=["january"]),
            Language(name="Anglais", level="C1", sources=["cv", "january"]),
            Language(name="Italien", level="B1", sources=["cv", "january"]),
        ]
    )
    draft = _bare(
        languages=[
            Language(name="Allemand", level="B1"),
            Language(name="Anglais", level="C2"),
            Language(name="Italien"),
        ]
    )
    merged = _merge(previous, draft)
    levels = {lang.name: lang.level for lang in merged.languages}
    assert levels == {"Allemand": "B1", "Anglais": "C2", "Italien": "B1"}
