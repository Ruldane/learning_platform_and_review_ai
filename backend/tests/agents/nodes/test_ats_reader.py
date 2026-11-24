"""Lecteur ATS (D129) : le contexte rendu au modèle (faits avec identifiants, CV sans coordonnées,
tout encadré), le prompt (base ATS datée, règles d'honnêteté), les défauts renvoyés au modèle et
le tri des propositions valables."""

from app.agents.nodes.review_common import (
    context_vars,
    cv_text,
    facts_text,
    keep_valid,
    problems_text,
    proposal_issues,
)
from app.agents.prompts.loader import render_prompt
from app.agents.tools.cv_compose import base_content
from app.agents.tools.review_schema import AtsReading, CompanyBrief
from tests.support.cv_review import ORDER, FakeCvReviewStore, compose_profile, rewrite

START = "<<<CONTENU_NON_FIABLE"


async def _vars(**over: object) -> dict[str, object]:
    store = FakeCvReviewStore()
    ctx = await store.context("u", "00000000-0000-4000-8000-0000000000aa")
    assert ctx.analysis is not None
    brief = CompanyBrief(summary="Éditeur.", values=["Sobriété"], stack=[])
    return context_vars(ctx, ctx.analysis, brief, "Greenhouse") | over


def test_facts_carry_ids_and_cv_membership() -> None:
    text = facts_text(compose_profile())
    assert "[x1a1] Réduit les coûts de 30 %" in text
    assert "[x2] Data Analyst — Autre Société (hors du CV)" in text
    assert "[c3] Kubernetes (hors du CV)" in text and "[c1] Python\n" in text


def test_cv_text_has_fact_ids_and_no_contact() -> None:
    profile = compose_profile()
    text = cv_text(base_content(profile, ORDER), profile)
    assert "Accroche : [t1] Ingénieure IA" in text
    assert "  - [x1a1] Réduit les coûts de 30 %" in text and "## Compétences (skills)" in text
    assert "example.org" not in text and "Lyon" not in text


async def test_every_input_is_untrusted() -> None:
    variables = await _vars()
    for key in ("posting", "analysis", "brief", "profile", "cv"):
        assert str(variables[key]).startswith(START), key
    assert variables["ats"] == "Greenhouse"
    assert '<<<CONTENU_NON_FIABLE source="offre:exigences non couvertes">>>' in str(
        variables["indicators"]
    )
    assert "Contrôle échoué : 1 intitulé n'est pas usuel." in str(variables["indicators"])


async def test_prompt_has_dated_ats_base_and_honesty_rules() -> None:
    prompt = render_prompt("ats_reader", mode="propose", prefix="a", **await _vars())
    assert "Updated: 2026-11-13" in prompt and "Notes per ATS" in prompt
    assert "Add no fact" in prompt and "Cite the fact identifiers" in prompt
    assert "No guarantee of passing an ATS" in prompt
    assert 'your references all start with "a"' in prompt
    assert "ATS Reader" in prompt and "Cross-examination" not in prompt


def test_issues_name_refs_and_ids_only() -> None:
    profile = compose_profile()
    items = [
        rewrite("x1a1", "Texte secret du CV", ref="r1"),
        rewrite("x9a9", "Autre texte secret", ref="a2"),
    ]
    issues = proposal_issues(items, profile, "a")
    assert issues[0] == "La référence r1 n'est pas à toi : tes références commencent par « a »."
    assert any("a2 vise un fait qui n'est pas dans le profil" in issue for issue in issues)
    assert "secret" not in problems_text(issues)


def test_keep_valid_drops_faulty_and_duplicate_refs() -> None:
    profile = compose_profile()
    items = [
        rewrite("x1a1", "Réduit les coûts", ref="a1"),
        rewrite("x1a2", "Anime", ref="a1"),
        rewrite("x9a9", "Inconnu", ref="a2"),
        rewrite("x1a2", "Anime l'équipe", ref="a3"),
    ]
    assert [p.ref for p in keep_valid(items, profile, "a")] == ["a1", "a3"]


def test_notes_are_shortened_not_refused() -> None:
    found = AtsReading.model_validate({"items": [], "notes": ["Une note. " * 60]})
    assert len(found.notes[0]) <= 300
