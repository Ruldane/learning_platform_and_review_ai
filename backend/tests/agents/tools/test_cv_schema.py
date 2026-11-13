"""Profil maître (6.2) : identifiants stables des faits, faits lisibles, faits venus du CV."""

from typing import Any

import pytest
from pydantic import ValidationError

from app.agents.tools.cv_schema import (
    Education,
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
    in_cv,
)


def exp(id: str = "", achievements: int = 1, **kwargs: Any) -> Experience:
    lines = [Line(text=f"Réalisation {n}") for n in range(1, achievements + 1)]
    fields: dict[str, Any] = {"role": "Développeuse", "company": "Société Fictive"} | kwargs
    return Experience(id=id, achievements=lines, **fields)


def profile(**kwargs: Any) -> MasterProfileData:
    return MasterProfileData(identity=Identity(name="Camille Exemple"), **kwargs)


def test_assign_fact_ids_keeps_existing_and_numbers_new() -> None:
    p = assign_fact_ids(profile(experiences=[exp(id="x1"), exp(id="")]))
    assert [e.id for e in p.experiences] == ["x1", "x2"]
    assert p.experiences[1].achievements[0].id == "x2a1"
    assert p.experiences[0].achievements[0].id == "x1a1"


def test_new_ids_follow_the_largest_taken_and_input_is_untouched() -> None:
    source = profile(experiences=[exp(), exp(id="x7")], skills=[SkillFact(name="Python")])
    p = assign_fact_ids(source)
    assert [e.id for e in p.experiences] == ["x8", "x7"]
    assert p.skills[0].id == "c1"
    assert source.experiences[0].id == ""


def test_duplicate_or_malformed_id_is_reassigned() -> None:
    first = exp(id="x2", achievements=0)
    first.achievements = [
        Line(id="x2a1", text="a"),
        Line(id="x2a1", text="b"),
        Line(id="x9", text="c"),
    ]
    p = assign_fact_ids(profile(experiences=[first, exp(id="x2"), exp(id="X3"), exp(id="x03")]))
    assert [e.id for e in p.experiences] == ["x2", "x3", "x4", "x5"]
    assert [line.id for line in p.experiences[0].achievements] == ["x2a1", "x2a2", "x2a3"]
    # Un enfant garde son id seulement s'il commence par celui de son parent.
    moved = exp(id="", achievements=0)
    moved.achievements = [Line(id="x1a1", text="a")]
    p = assign_fact_ids(profile(experiences=[exp(id="x1", achievements=0), moved]))
    assert p.experiences[1].achievements[0].id == "x2a1"


def test_every_kind_has_its_prefix() -> None:
    p = assign_fact_ids(
        profile(
            title=Line(text="Ingénieure IA"),
            summary=Line(text="Résumé"),
            experiences=[exp()],
            education=[Education(degree="Master", school="Université", details=[Line(text="d")])],
            skills=[SkillFact(name="Python")],
            projects=[Project(name="Tremplin", achievements=[Line(text="a")])],
            languages=[Language(name="Anglais", level="C1")],
            links=[Link(label="GitHub", url="https://example.org/camille")],
        )
    )
    assert set(facts_of(p)) == {
        "t1",
        "s1",
        "x1",
        "x1a1",
        "f1",
        "f1d1",
        "c1",
        "p1",
        "p1a1",
        "l1",
        "k1",
    }


def test_facts_of_and_in_cv() -> None:
    p = assign_fact_ids(
        profile(
            title=Line(text="Ingénieure IA"),
            experiences=[
                exp(sources=["cv", "linkedin"]),
                exp(role="Stagiaire", sources=["linkedin"]),
            ],
            skills=[
                SkillFact(name="Python", sources=["cv"]),
                SkillFact(name="Rust", sources=["note"]),
            ],
            languages=[Language(name="Anglais", level="C1", sources=["january"])],
        )
    )
    facts = facts_of(p)
    assert facts["x1"] == "Développeuse — Société Fictive"
    assert facts["x2a1"] == "Réalisation 1"
    assert (facts["c2"], facts["l1"], facts["t1"]) == ("Rust", "Anglais — C1", "Ingénieure IA")
    assert in_cv(p) == {"t1", "x1", "x1a1", "c1"}


def test_unnumbered_facts_are_omitted() -> None:
    assert facts_of(profile(experiences=[exp()])) == {}
    assert in_cv(profile(experiences=[exp(sources=["cv"])])) == set()


@pytest.mark.parametrize("start", ["2024-13", "24-01", "janvier 2024"])
def test_dates_are_year_or_year_month(start: str) -> None:
    assert exp(start="2024-01", end="2025").end == "2025"
    with pytest.raises(ValidationError):
        exp(start=start)
