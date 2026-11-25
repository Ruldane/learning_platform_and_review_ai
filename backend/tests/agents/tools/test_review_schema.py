"""Propositions du Lecteur ATS et du Recruteur (6.12) : formes acceptées, identifiants de faits
sans borne, phrases rendues au modèle."""

import re
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
    SourcedLine,
    assign_fact_ids,
    facts_of,
)
from app.agents.tools.review_schema import (
    FACT_ID,
    CompanyBrief,
    Confrontation,
    Proposal,
    ProposalList,
    Stance,
    proposal_problems,
    section_of,
)


def profile() -> MasterProfileData:
    """Un profil à identifiants à trois chiffres : `x12a14`, `c100`, `x1` (le seul du CV), `c1`."""
    experiences = [
        Experience(
            role=f"Rôle {n}",
            company="Société Fictive",
            achievements=[Line(text=f"Réalisation {n}.{m}") for m in range(1, 15)],
            sources=["cv"] if n == 1 else ["linkedin"],
        )
        for n in range(1, 13)
    ]
    return assign_fact_ids(
        MasterProfileData(
            identity=Identity(name="Camille Exemple"),
            title=SourcedLine(text="Ingénieure IA", sources=["cv"]),
            summary=SourcedLine(text="Résumé", sources=["linkedin"]),
            experiences=experiences,
            education=[
                Education(degree="Master", school="École Fictive", details=[Line(text="Mention")])
            ],
            skills=[
                SkillFact(id=f"c{n}", name=f"Compétence {n}", sources=["cv"]) for n in (1, 100)
            ],
            projects=[Project(name="Projet", achievements=[Line(text="Résultat")])],
            languages=[Language(name="Français")],
            links=[Link(label="Site", url="https://example.org")],
        )
    )


P = profile()


def proposal(ref: str = "a1", **kw: Any) -> Proposal:
    fields: dict[str, Any] = {
        "ref": ref,
        "section": "experience",
        "action": "rewrite",
        "target": "x1a1",
        "after": "Nouveau texte",
        "reason": "Plus clair.",
        "type": "clarity",
    } | kw
    return Proposal(**fields)


def test_fact_id_matches_every_real_fact_id() -> None:
    ids = list(facts_of(P))
    assert {"x12a14", "c100", "t1", "s1", "f1d1", "p1a1", "l1", "k1"} <= set(ids)
    assert [i for i in ids if not re.match(FACT_ID, i)] == []


@pytest.mark.parametrize("bad", ["X1", "x", "x1a", "x1b2", "a1", "x1a1a1", "x-1", "x1 ", "1x"])
def test_fact_id_rejects_malformed_ids(bad: str) -> None:
    assert re.match(FACT_ID, bad) is None
    with pytest.raises(ValidationError):
        proposal(target=bad)
    with pytest.raises(ValidationError):
        proposal(fact_ids=[bad])


def test_proposal_accepts_ids_beyond_two_digits() -> None:
    p = proposal(target="x12a14", fact_ids=["c100", "x12"])
    assert p.target == "x12a14"


@pytest.mark.parametrize("ref", ["m3", "a", "a100", "r", "A1", "a1 ", "1a"])
def test_ref_pattern(ref: str) -> None:
    with pytest.raises(ValidationError):
        proposal(ref=ref)


def test_bounds() -> None:
    with pytest.raises(ValidationError):
        proposal(after="x" * 601)
    with pytest.raises(ValidationError):
        proposal(fact_ids=["x1"] * 7)
    with pytest.raises(ValidationError):
        ProposalList(items=[proposal(ref=f"a{n}") for n in range(26)])
    assert len(ProposalList(items=[proposal(ref=f"a{n}") for n in range(25)]).items) == 25
    with pytest.raises(ValidationError):
        Confrontation(stances=[Stance(ref="a1", stance="keep", reason="ok")] * 51)
    with pytest.raises(ValidationError):
        CompanyBrief(summary="Résumé", values=["v"] * 7, stack=[])
    with pytest.raises(ValidationError):
        Stance(ref="a1", stance="maybe", reason="ok")  # type: ignore[arg-type]


def test_long_reason_is_shortened_not_refused() -> None:
    assert len(proposal(reason="Mot. " * 200).reason) <= 300


def test_section_of() -> None:
    assert [section_of(i) for i in ("t1", "s2", "x1a1", "f1d1", "c100", "p1", "l1", "k1")] == [
        "summary", "summary", "experience", "education", "skills", "projects", "languages", "links",
    ]  # fmt: skip
    assert section_of("z1") is None


def test_valid_proposals_have_no_problem() -> None:
    items = [
        proposal("a1"),
        proposal("a2", action="add", target="x2a1", after="Texte"),
        proposal("a3", action="remove", target="x1a2", after=""),
        proposal("r1", action="move", section="skills", target=None, after="experience"),
    ]
    assert proposal_problems(items, P) == []


def test_unknown_fact_and_double_ref() -> None:
    items = [
        proposal("a1", target="x99a1"),
        proposal("a1", fact_ids=["x1a1", "c999"]),
    ]
    problems = proposal_problems(items, P)
    assert len(problems) == 3
    assert any("a1" in p and "twice" in p for p in problems)
    assert any("not in the profile" in p for p in problems)
    assert any("c999" in p for p in problems)


def test_add_of_a_fact_already_in_the_cv_and_remove_of_an_absent_one() -> None:
    problems = proposal_problems(
        [
            proposal("a1", action="add", target="x1a1"),
            proposal("a2", action="remove", target="x2a1", after=""),
            proposal("a3", action="rewrite", target="x2a1"),
        ],
        P,
    )
    assert len(problems) == 3
    assert "already in the CV" in problems[0]
    assert all("absent from the CV" in p for p in problems[1:])


def test_target_required_text_required_and_section_must_match() -> None:
    problems = proposal_problems(
        [
            proposal("a1", target=None),
            proposal("a2", action="add", target="x2a1", after=" "),
            proposal("a3", target="x1a1", section="skills"),
        ],
        P,
    )
    assert [("a1" in p, "a2" in p, "a3" in p) for p in problems] == [
        (True, False, False), (False, True, False), (False, False, True),
    ]  # fmt: skip


def test_move_needs_another_section_key() -> None:
    bad = [
        proposal("a1", action="move", target=None, after="nowhere"),
        proposal("a2", action="move", target=None, after="experience"),
    ]
    assert len(proposal_problems(bad, P)) == 2


def test_problems_never_quote_the_proposal_text() -> None:
    text = "Zxqvwy secret"
    problems = proposal_problems([proposal(target="x99a1", after=text, reason=text)], P)
    assert problems
    assert not any("Zxqvwy" in p for p in problems)
