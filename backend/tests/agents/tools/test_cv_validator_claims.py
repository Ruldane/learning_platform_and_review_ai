"""Validateur des modifications (6.12) : proposition sans fait cité, titres, noms propres, raisons
sans texte du CV."""

import pytest

from app.agents.tools.cv_schema import SourcedLine
from app.agents.tools.cv_validator import GAP, NAME, NO_FACT, NUMBER, RATIO, TITLE, TOOL, validate
from tests.support.cv_review import A, add, analysis, profile, proposal, rewrite

# --- proposition sans fait ---


def test_rewrite_with_unknown_target_and_no_fact_needs_confirmation() -> None:
    v = validate(rewrite("x9a9", "Certifiée en cybersécurité"), profile(), A)
    assert v.status == "to_confirm"
    assert v.blocks[0] == NO_FACT


def test_add_with_unknown_target_is_not_ok() -> None:
    v = validate(add("c9", "Certifiée en cybersécurité"), profile(skills=["Docker"]), A)
    assert v.status == "to_confirm"
    assert NO_FACT in v.blocks


def test_proposal_citing_no_fact_ids_relies_on_its_target() -> None:
    v = validate(rewrite("x1a1", "Réalisation soignée", fact_ids=[]), profile(), A)
    assert v.status == "ok"


def test_unknown_fact_ids_are_not_references() -> None:
    v = validate(
        rewrite("x9a9", "Coûts réduits de 30 %", fact_ids=["x8a8"]),
        profile(line="Coûts réduits de 30 %"),
        A,
    )
    assert v.status == "to_confirm"
    assert NO_FACT in v.blocks


# --- titres ---


def test_new_title_blocks() -> None:
    v = validate(
        rewrite("x1", "Lead AI Engineer — Société Fictive"), profile(role="AI Engineer"), A
    )
    assert v.status == "to_confirm"
    assert TITLE in v.blocks


def test_title_word_present_in_the_roles_is_ok() -> None:
    v = validate(
        rewrite("x1", "Senior AI Engineer — Société Fictive"), profile(role="Senior AI Engineer"), A
    )
    assert v.status == "ok"


def test_title_word_present_in_the_profile_title_is_ok() -> None:
    p = profile(title=SourcedLine(text="Lead Data Engineer", sources=["cv"]))
    assert validate(rewrite("x1a1", "Réalisation de lead technique"), p, A).status == "ok"


def test_responsable_is_a_title_claim() -> None:
    v = validate(
        rewrite("x1a1", "Responsable de la migration"), profile(line="Participe à la migration"), A
    )
    assert TITLE in v.blocks


def test_posting_title_claimed_without_being_a_role() -> None:
    v = validate(
        rewrite("x1a1", "Data Scientist chez Société Fictive"), profile(role="AI Engineer"), A
    )
    assert v.status == "to_confirm"
    assert TITLE in v.blocks


def test_posting_title_that_is_a_role_is_ok() -> None:
    v = validate(rewrite("x1a1", "Travail de data scientist"), profile(role="Data Scientist"), A)
    assert v.status == "ok"


# --- noms propres ---


def test_unknown_proper_noun_needs_confirmation() -> None:
    v = validate(rewrite("x1a1", "Entrepôt de données sur Snowflake"), profile(), A)
    assert v.status == "to_confirm"
    assert NAME in v.blocks or TOOL in v.blocks


def test_unknown_company_name_needs_confirmation() -> None:
    v = validate(rewrite("x1a1", "Projet mené chez Globex Corporation"), profile(), A)
    assert v.blocks == [NAME]


def test_proper_noun_in_the_profile_and_sentence_start_are_ok() -> None:
    v = validate(
        rewrite("x1a1", "Pilote la refonte chez Société Fictive. Livre en avance."), profile(), A
    )
    assert v.status == "ok"


def test_single_word_skill_is_checked() -> None:
    v = validate(add("c1", "Looker"), profile(skills=["Tableau noir"]), A)
    assert v.status == "to_confirm"


# --- sans texte, honnêteté des raisons ---


def test_remove_and_move_write_no_text() -> None:
    assert validate(proposal("remove", "x1a1", ""), profile(), A).status == "ok"
    move = proposal("move", None, "skills", section="education")
    assert validate(move, profile(), A).status == "ok"


def test_plain_rewrite_of_a_fact_is_ok() -> None:
    v = validate(rewrite("x1a1", "Réalisation clairement formulée"), profile(), A)
    assert (v.status, v.blocks, v.gap_terms) == ("ok", [], [])


def test_blocks_never_quote_cv_text() -> None:
    after = "Zxqvwy kubernetes AWS Globex 45 % moitié lead Snowflakery"
    v = validate(rewrite("x1a1", after), profile(), analysis(keywords=["AWS"]))
    fixed = {NO_FACT, NUMBER, RATIO, TOOL, NAME, TITLE, GAP}
    assert v.blocks
    assert set(v.blocks) <= fixed
    quoted = [
        w for w in after.lower().split() if len(w) > 3 and any(w in b.lower() for b in v.blocks)
    ]
    assert quoted == []


# --- revue 6.12 : minors ---


def test_text_after_a_colon_or_semicolon_is_not_a_sentence_start() -> None:
    for after in ("Stack : Streamlit", "Outils ; Streamlit"):
        assert validate(rewrite("x1a1", after), profile(), A).blocks == [NAME]


@pytest.mark.parametrize(
    "after", ["Staff AI Engineer", "Consultant AI Engineer", "Director of AI", "Chief AI Officer"]
)
def test_more_title_words(after: str) -> None:
    assert TITLE in validate(rewrite("x1", after), profile(role="AI Engineer"), A).blocks


def test_the_location_of_an_experience_is_known_text() -> None:
    p = profile()
    p.experiences[0].location = "Montpellier"
    assert validate(rewrite("x1a1", "Projet mené à Montpellier"), p, A).status == "ok"


def test_gap_block_says_the_cited_facts_not_the_profile() -> None:
    v = validate(rewrite("x1a1", "Pilote Terraform"), profile(), analysis(tools=["Terraform"]))
    assert "cited facts" in GAP
    assert GAP in v.blocks
