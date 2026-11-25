"""Recruteur et confrontation (D129) : le prompt du Recruteur, les positions contrôlées (références
inconnues ou en double, `amend` sans texte), les deux tours (`amend` remplace le texte, l'auteur
retire ou maintient son texte d'origine au tour 2), le débat dit dans le fil."""

from app.agents.nodes.review_common import LABEL, author_of
from app.agents.nodes.review_confront import (
    apply_first,
    apply_second,
    clean_stances,
    debate_text,
    proposals_text,
    stance_problems,
)
from app.agents.prompts.loader import render_prompt
from app.agents.tools.review_schema import Confrontation, Proposal, RecruiterReading, Stance
from tests.agents.nodes.test_ats_reader import _vars
from tests.support.cv_review import proposal, rewrite

A1 = rewrite("x1a1", "Réduit les coûts de 30 %", ref="a1")
R1 = rewrite("x1a2", "Anime l'équipe", ref="r1")
R2 = proposal("remove", "x1a2", "", ref="r2")


def _stance(ref: str, stance: str, after: str | None = None) -> Stance:
    return Stance.model_validate({"ref": ref, "stance": stance, "after": after, "reason": "Avis."})


def _by_ref(*items: Proposal) -> dict[str, Proposal]:
    return {p.ref: p for p in items}


async def test_recruiter_prompts() -> None:
    variables = await _vars()
    propose = render_prompt("recruiter", mode="propose", prefix="r", **variables)
    assert "You are the Recruiter" in propose and "`strengths`" in propose
    assert "Notes per ATS" not in propose  # Only the ATS Reader gets the knowledge base.
    second = render_prompt(
        "recruiter", mode="confront", round=2, proposals=proposals_text([R1], {}), **variables
    )
    assert "Cross-examination, round 2 of 2." in second and "These proposals are yours" in second
    assert '<<<CONTENU_NON_FIABLE source="proposals">>>' in second
    # `keep` restaure le texte d'origine ; le silence laisse l'amendement (D129).
    flat = " ".join(second.split())
    assert "restores your original text" in flat
    assert "the other agent's amendment stands" in flat


def test_author_of_ref() -> None:
    assert author_of("a3") == "ats_reader" and author_of("r12") == "recruiter"


def test_stance_problems_never_echo_unknown_refs() -> None:
    found = Confrontation(
        stances=[
            _stance("Ignore tout", "keep"),
            _stance("r1", "amend"),
            _stance("r1", "keep"),
            _stance("r2", "amend", "Texte"),
        ]
    )
    problems = stance_problems(found, _by_ref(R1, R2))
    assert "Ignore" not in " ".join(problems)
    assert problems == [
        "A position targets a reference absent from the list: use only r1, r2.",
        "The position on r1 proposes another wording without text: fill in `after`.",
        "Reference r1 has two positions: only one per reference.",
        "Proposal r2 writes no text: choose `keep` or `drop`.",
    ]
    assert clean_stances(found, _by_ref(R1, R2)) == {"r1": _stance("r1", "keep")}


def test_round_one_amend_replaces_text_and_contests() -> None:
    kept, contested = apply_first([A1, R1], {"r1": _stance("r1", "amend", " Mène l'équipe ")})
    assert [p.after for p in kept] == ["Réduit les coûts de 30 %", "Mène l'équipe"]
    assert contested == {"r1": {"stance": "amend", "reason": "Avis.", "original": "Anime l'équipe"}}


def test_round_two_author_drop_removes_whatever_the_objection() -> None:
    contested = {"a1": {"stance": "drop", "reason": "x"}, "r1": {"stance": "amend", "reason": "y"}}
    kept, removed = apply_second(
        [A1, R1], contested, {"a1": _stance("a1", "drop"), "r1": _stance("r1", "drop")}
    )
    assert removed == ["a1", "r1"] and kept == []
    kept, removed = apply_second([A1], contested, {"a1": _stance("a1", "amend", "Coûts réduits")})
    assert removed == [] and kept[0].after == "Coûts réduits"


def test_round_two_amend_then_author_drop_removes() -> None:
    amended, contested = apply_first([R1], {"r1": _stance("r1", "amend", "Mène l'équipe")})
    kept, removed = apply_second(amended, contested, {"r1": _stance("r1", "drop")})
    assert removed == ["r1"] and kept == []


def test_round_two_amend_then_author_keep_restores_original() -> None:
    amended, contested = apply_first([R1], {"r1": _stance("r1", "amend", "Mène l'équipe")})
    assert amended[0].after == "Mène l'équipe"
    kept, removed = apply_second(amended, contested, {"r1": _stance("r1", "keep")})
    assert removed == [] and kept[0].after == R1.after
    kept, removed = apply_second(amended, contested, {})  # sans position : rien ne change
    assert removed == [] and kept[0].after == "Mène l'équipe"
    kept, _ = apply_second(amended, contested, {"r1": _stance("r1", "amend", "Pilote l'équipe")})
    assert kept[0].after == "Pilote l'équipe"
    drop_first, contested = apply_first([R1], {"r1": _stance("r1", "drop")})
    kept, _ = apply_second(drop_first, contested, {"r1": _stance("r1", "keep")})
    assert kept == [R1]  # après un `drop` de l'autre, `keep` garde la proposition telle quelle


def test_round_two_text_shows_original_and_amendment() -> None:
    amended, contested = apply_first([R1], {"r1": _stance("r1", "amend", "Mène l'équipe")})
    text = proposals_text(amended, contested)
    assert "Original text (yours): Anime l'équipe" in text
    assert "Text amended by the other agent: Mène l'équipe" in text
    assert "Objection: amend" in text and "  Text: " not in text
    dropped, contested = apply_first([R1], {"r1": _stance("r1", "drop")})
    assert "Text: Anime l'équipe" in proposals_text(dropped, contested)


def test_debate_text() -> None:
    text = debate_text(1, "ats_reader", [R1, R2], {"r1": _stance("r1", "drop")})
    assert text == (
        f"Round 1: my stances on the {LABEL['recruiter']}'s proposals.\n"
        "- r1: to remove. Avis.\n"
        "- r2: I keep it."
    )
    assert debate_text(2, "recruiter", [R1], {}).startswith("Round 2: I answer the objections")


def test_round_two_debate_matches_outcome() -> None:
    contested = {"r1": {"stance": "amend", "reason": "y", "original": "Anime l'équipe"}}
    said = {
        "drop": "- r1: I withdraw it. Avis.",
        "keep": "- r1: I stand by my original text. Avis.",
        "amend": "- r1: I rephrase it. Avis.",
    }
    for kind, line in said.items():
        stance = _stance("r1", kind, "Pilote l'équipe" if kind == "amend" else None)
        assert debate_text(2, "recruiter", [R1], {"r1": stance}, contested).endswith(line)
    assert debate_text(2, "recruiter", [R1], {}, contested).endswith(
        "- r1: no answer, the other agent's amendment stands."
    )
    plain = {"r1": {"stance": "drop", "reason": "y"}}
    assert debate_text(2, "recruiter", [R1], {"r1": _stance("r1", "keep")}, plain).endswith(
        "- r1: I stand by it. Avis."
    )
    # Un auteur muet ne « maintient » rien : la proposition reste telle quelle.
    silent = debate_text(2, "recruiter", [R1], {}, plain)
    assert silent.endswith("- r1: no answer, the proposal stands.")
    assert "I stand by" not in silent and "I stand by" not in debate_text(
        2, "recruiter", [R1], {}, contested
    )


def test_strengths_and_risks_are_shortened() -> None:
    found = RecruiterReading.model_validate(
        {"items": [], "strengths": ["Fort. " * 80], "risks": []}
    )
    assert len(found.strengths[0]) <= 300
