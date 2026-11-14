"""Recruteur et confrontation (D129) : le prompt du Recruteur, les positions contrôlées (références
inconnues ou en double, `amend` sans texte), les deux tours (`drop` des deux côtés retire,
`amend` remplace le texte), le débat dit dans le fil."""

from app.agents.nodes.review_common import author_of
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
    assert "Tu es le Recruteur" in propose and "`strengths`" in propose
    assert "Mise à jour : 2026-11-13" not in propose  # la base ATS est au Lecteur ATS
    second = render_prompt(
        "recruiter", mode="confront", round=2, proposals=proposals_text([R1], {}), **variables
    )
    assert (
        "Confrontation, tour 2 sur 2." in second and "Ces propositions sont les tiennes" in second
    )
    assert '<<<CONTENU_NON_FIABLE source="propositions">>>' in second


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
        "Une position vise une référence absente de la liste : n'emploie que r1, r2.",
        "La position sur r1 propose une autre formulation sans texte : renseigne `after`.",
        "La référence r1 a deux positions : une seule par référence.",
        "La proposition r2 n'écrit aucun texte : choisis `keep` ou `drop`.",
    ]
    assert clean_stances(found, _by_ref(R1, R2)) == {"r1": _stance("r1", "keep")}


def test_round_one_amend_replaces_text_and_contests() -> None:
    kept, contested = apply_first([A1, R1], {"r1": _stance("r1", "amend", " Mène l'équipe ")})
    assert [p.after for p in kept] == ["Réduit les coûts de 30 %", "Mène l'équipe"]
    assert contested == {"r1": {"stance": "amend", "reason": "Avis."}}


def test_round_two_needs_both_drops() -> None:
    contested = {"a1": {"stance": "drop", "reason": "x"}, "r1": {"stance": "amend", "reason": "y"}}
    kept, removed = apply_second(
        [A1, R1], contested, {"a1": _stance("a1", "drop"), "r1": _stance("r1", "drop")}
    )
    assert removed == ["a1"] and [p.ref for p in kept] == ["r1"]
    kept, removed = apply_second([A1], contested, {"a1": _stance("a1", "amend", "Coûts réduits")})
    assert removed == [] and kept[0].after == "Coûts réduits"


def test_debate_text() -> None:
    text = debate_text(1, "ats_reader", [R1, R2], {"r1": _stance("r1", "drop")})
    assert text == (
        "Tour 1 : mes positions sur les propositions du Recruteur.\n"
        "- r1 : à retirer. Avis.\n"
        "- r2 : je garde."
    )
    assert debate_text(2, "recruiter", [R1], {}).startswith("Tour 2 : je réponds aux objections")


def test_strengths_and_risks_are_shortened() -> None:
    found = RecruiterReading.model_validate(
        {"items": [], "strengths": ["Fort. " * 80], "risks": []}
    )
    assert len(found.strengths[0]) <= 300
