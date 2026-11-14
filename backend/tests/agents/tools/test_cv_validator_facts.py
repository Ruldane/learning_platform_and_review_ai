"""Validateur des modifications (revue finale BA-C1) : la réécriture d'un fait structuré (rôle,
diplôme, langue et niveau, lien, compétence, titre) ne dit que des mots du profil ; une URL ne
change jamais."""

import pytest

from app.agents.tools.cv_schema import (
    Education,
    Experience,
    Identity,
    Language,
    Line,
    Link,
    MasterProfileData,
    SkillFact,
    SourcedLine,
    assign_fact_ids,
)
from app.agents.tools.cv_validator import validate
from app.agents.tools.cv_validator_facts import FOREIGN
from app.agents.tools.posting_schema import PostingAnalysis
from tests.support.cv_review import analysis, rewrite

OFFER: PostingAnalysis = analysis(title="Ingénieur IA (H/F)")


def structured() -> MasterProfileData:
    return assign_fact_ids(
        MasterProfileData(
            identity=Identity(name="Camille Exemple"),
            title=SourcedLine(text="Développeuse IA", sources=["cv"]),
            experiences=[
                Experience(role="Développeuse", company="Société Fictive", sources=["cv"])
            ],
            education=[
                Education(
                    degree="Licence informatique", school="Université Exemple", sources=["cv"]
                )
            ],
            skills=[SkillFact(name="Python", sources=["cv"])],
            languages=[Language(name="Anglais", level="B2", sources=["cv"])],
            links=[Link(label="GitHub", url="https://github.com/camille-exemple", sources=["cv"])],
        )
    )


@pytest.mark.parametrize(
    ("target", "after"),
    [
        ("t1", "Ingénieure IA"),  # le féminin de l'intitulé de l'offre
        ("t1", "Ingénieur IA"),
        ("x1", "Ingénieure data — Société Fictive"),
        ("f1", "Doctorat informatique — Université Exemple"),
        ("f1", "Master informatique — Université Exemple"),
        ("l1", "Anglais — C1"),
        ("l1", "Anglais — courant"),
        ("k1", "GitHub — https://attacker.example/camille"),
        ("k1", "GitHub — https://github.com/autre-compte"),
        ("c1", "Python (expert)"),
    ],
)
def test_rewrite_of_a_structured_fact_with_a_foreign_word_needs_confirmation(
    target: str, after: str
) -> None:
    v = validate(rewrite(target, after), structured(), OFFER)
    assert v.status == "to_confirm"
    assert FOREIGN in v.blocks


@pytest.mark.parametrize(
    ("target", "after"),
    [
        ("t1", "Développeuse IA"),
        ("t1", "développeuse ia"),
        ("x1", "Développeuse — Société Fictive"),
        ("x1", "Société Fictive — Développeuse"),
        ("f1", "Licence informatique, Université Exemple"),
        ("l1", "Anglais — B2"),
        ("k1", "GitHub — https://github.com/camille-exemple"),
        ("k1", "https://github.com/camille-exemple/"),
        ("c1", "Python"),
        ("c1", "python"),
    ],
)
def test_rewrite_of_a_structured_fact_with_its_own_words_stays_ok(target: str, after: str) -> None:
    assert validate(rewrite(target, after), structured(), OFFER).status == "ok"


def test_a_word_of_another_role_of_the_profile_is_allowed() -> None:
    data = structured()
    data.experiences[0].role = "Ingénieur IA"  # le rôle existe au profil
    assert validate(rewrite("t1", "Ingénieur IA"), data, OFFER).status == "ok"


def test_the_feminine_is_not_the_masculine_unless_both_are_in_the_profile() -> None:
    data = structured()
    data.experiences[0].role = "Ingénieur IA"
    v = validate(rewrite("t1", "Ingénieure IA"), data, OFFER)
    assert v.status == "to_confirm"
    data.experiences[0].role = "Ingénieure IA"
    assert validate(rewrite("t1", "Ingénieure IA"), data, OFFER).status == "ok"


def test_a_free_line_is_not_a_structured_fact() -> None:
    data = structured()
    data.experiences[0].achievements = [Line(text="Réalisation")]
    data = assign_fact_ids(data)
    v = validate(rewrite("x1a1", "Réalisation soignée plus claire"), data, OFFER)
    assert FOREIGN not in v.blocks


def siblings() -> MasterProfileData:
    """Le profil de `structured()` avec un second fait de chaque sorte (l2, f2, k2) et une
    réalisation qui dit « experts » (x1a1)."""
    data = structured()
    data.experiences[0].achievements = [Line(text="Formé des développeurs experts en Python")]
    data.education.append(Education(degree="Master gestion", school="École B", sources=["cv"]))
    data.languages.append(Language(name="Espagnol", level="C1", sources=["cv"]))
    data.links.append(Link(label="LinkedIn", url="https://linkedin.com/in/camille", sources=["cv"]))
    return assign_fact_ids(data)


@pytest.mark.parametrize(
    ("target", "after", "cited"),
    [
        ("l1", "Anglais — C1", "l2"),  # le niveau d'une autre langue
        ("f1", "Master informatique — Université Exemple", "f2"),  # le diplôme d'un autre
        ("c1", "Python (expert)", "x1a1"),  # un mot d'une réalisation
        ("k1", "GitHub — https://linkedin.com/in/camille", "k2"),  # l'URL d'un autre lien
    ],
)
def test_citing_a_sibling_fact_never_lifts_the_structured_word_check(
    target: str, after: str, cited: str
) -> None:
    v = validate(rewrite(target, after, fact_ids=[cited]), siblings(), OFFER)
    assert v.status == "to_confirm"
    assert FOREIGN in v.blocks


def with_senior_role() -> MasterProfileData:
    """Le profil de `structured()` avec un second rôle « Lead Développeuse Senior » (x2)."""
    data = structured()
    data.experiences.append(
        Experience(role="Lead Développeuse Senior", company="Autre SA", sources=["cv"])
    )
    return assign_fact_ids(data)


@pytest.mark.parametrize(
    ("target", "after"),
    [
        ("x1", "Lead Développeuse — Société Fictive"),  # une promotion que le profil ne dit pas
        ("x1", "Senior Développeuse — Société Fictive"),
        ("c1", "Python (senior)"),
        ("c1", "Python Lead"),
        ("l1", "Anglais — B2 Senior"),
        ("f1", "Licence informatique Lead — Université Exemple"),
    ],
)
def test_the_roles_of_the_profile_only_lift_a_title_target(target: str, after: str) -> None:
    v = validate(rewrite(target, after), with_senior_role(), OFFER)
    assert v.status == "to_confirm"
    assert FOREIGN in v.blocks


def test_a_title_target_may_use_a_role_of_the_profile() -> None:
    assert validate(rewrite("t1", "Lead Développeuse"), with_senior_role(), OFFER).status == "ok"
