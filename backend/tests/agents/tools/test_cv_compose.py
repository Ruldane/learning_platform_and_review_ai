"""Composition du CV ciblé (6.12, critère 18.3) : le contenu part des faits du CV d'origine,
chaque ligne porte un fait du profil, les modifications s'appliquent dans l'ordre remove, rewrite,
add, move et une cible introuvable est ignorée et comptée."""

from typing import Any

from app.agents.tools.cv_compose import apply_modifications, apply_with_report, base_content
from app.agents.tools.cv_schema import (
    CvContent,
    CvEntry,
    CvLine,
    CvSection,
    Identity,
    MasterProfileData,
    SectionKey,
    SkillFact,
    assign_fact_ids,
    facts_of,
    in_cv,
)
from app.agents.tools.review_schema import Proposal, section_of
from tests.support.cv_review import compose_profile

ORDER: list[SectionKey] = [
    "summary", "skills", "experience", "education", "projects", "languages", "links",
]  # fmt: skip


P = compose_profile()
BASE = base_content(P, ORDER)


def proposal(action: str, target: str | None, after: str = "", **kw: Any) -> Proposal:
    fields: dict[str, Any] = {
        "ref": "a1",
        "section": section_of(target) if target else "experience",
        "action": action,
        "target": target,
        "after": after,
        "reason": "Plus clair.",
        "type": "clarity",
    } | kw
    return Proposal(**fields)


def lines_of(content: CvContent) -> list[CvLine]:
    out: list[CvLine] = []
    for section in content.sections:
        out += section.items
        for entry in section.entries:
            out += entry.lines
    return out


def entries_of(content: CvContent) -> list[CvEntry]:
    return [entry for section in content.sections for entry in section.entries]


def section(content: CvContent, key: str) -> CvSection:
    return next(s for s in content.sections if s.key == key)


def texts(lines: list[CvLine]) -> list[str]:
    return [line.text for line in lines]


def keys(content: CvContent) -> list[str]:
    return [s.key for s in content.sections]


# --- contenu d'origine ---


def test_base_content_keeps_cv_facts_in_template_order() -> None:
    # Le résumé et les liens viennent de LinkedIn : absents ; les sections suivent le gabarit.
    assert keys(BASE) == ["skills", "experience", "education", "projects", "languages"]
    assert keys(base_content(P, ["languages", "experience", "skills"])) == [
        "languages",
        "experience",
        "skills",
    ]
    assert (BASE.name, BASE.headline, BASE.contact) == (
        "Camille Exemple",
        "Ingénieure IA",
        ["camille.exemple@example.org", "Lyon"],
    )
    assert texts(section(BASE, "skills").items) == ["Python", "Docker"]
    experience = section(BASE, "experience").entries
    assert [e.heading for e in experience] == ["AI Engineer — Société Fictive"]
    assert (experience[0].subheading, experience[0].dates) == ("Paris", "2021-03 – 2023-06")
    assert texts(experience[0].lines) == ["Réduit les coûts de 30 %", "Anime l'équipe"]
    project = section(BASE, "projects").entries[0]
    assert texts(project.lines) == ["Assistant interne", "Adopté par 40 personnes"]


def test_base_content_has_nothing_outside_the_cv() -> None:
    used = {i for line in lines_of(BASE) for i in line.fact_ids}
    used |= {e.fact_id for e in entries_of(BASE) if e.fact_id}
    assert used <= in_cv(P)
    assert {"x2", "x2a1", "c3", "k1", "s1"}.isdisjoint(used)


def test_composed_lines_all_have_fact_ids() -> None:
    """Aucune ligne sans fait (critère 18.3), avant et après modifications."""
    accepted = [
        proposal("rewrite", "x1a1", "Coûts réduits de 30 %", fact_ids=["x1a2"]),
        proposal("add", "x2a1", "Tableaux de bord construits"),
        proposal("add", "c3", "Kubernetes"),
        proposal("add", "s1", "Ingénieure IA passionnée"),
        proposal("add", "p1a1", "Adopté par 40 personnes"),
    ]
    facts = set(facts_of(P))
    for content in (BASE, apply_modifications(BASE, P, accepted)):
        lines = lines_of(content)
        assert lines
        assert all(line.fact_ids and set(line.fact_ids) <= facts for line in lines)
        assert all(e.fact_id in facts for e in entries_of(content))


def test_base_content_of_a_profile_without_cv_facts_is_empty() -> None:
    bare = assign_fact_ids(
        MasterProfileData(
            identity=Identity(name="Camille Exemple"),
            skills=[SkillFact(name="Python", sources=["note"])],
        )
    )
    content = base_content(bare, ORDER)
    assert (content.sections, content.headline) == ([], None)


# --- modifications ---


def test_apply_rewrite_add_remove_move() -> None:
    accepted = [
        proposal("move", None, "skills", section="experience", ref="a5"),
        proposal("add", "c3", "Kubernetes", ref="a4"),
        proposal("rewrite", "x1a1", "Coûts réduits de 30 %", ref="a2"),
        proposal("remove", "x1a2", ref="a3"),
        proposal("rewrite", "c1", "Python 3", ref="a1"),
    ]
    out = apply_modifications(BASE, P, accepted)
    assert keys(out) == ["experience", "skills", "education", "projects", "languages"]
    assert texts(section(out, "skills").items) == ["Python 3", "Docker", "Kubernetes"]
    assert texts(section(out, "experience").entries[0].lines) == ["Coûts réduits de 30 %"]
    assert base_content(P, ORDER) == BASE  # `base` n'est pas modifié


def test_rewrite_keeps_target_and_known_cited_facts_only() -> None:
    p = proposal("rewrite", "x1a1", "Coûts réduits, équipe animée", fact_ids=["x1a2", "x9a9"])
    line = section(apply_modifications(BASE, P, [p]), "experience").entries[0].lines[0]
    assert line.fact_ids == ["x1a1", "x1a2"]


def test_rewrite_entry_and_headline() -> None:
    out = apply_modifications(
        BASE,
        P,
        [
            proposal("rewrite", "x1", "AI Engineer — Société Fictive (Paris)"),
            proposal("rewrite", "t1", "Ingénieure en IA"),
        ],
    )
    assert section(out, "experience").entries[0].heading == "AI Engineer — Société Fictive (Paris)"
    assert out.headline == "Ingénieure en IA"


def test_remove_entry_line_headline_and_empty_section() -> None:
    out = apply_modifications(
        BASE, P, [proposal("remove", "x1"), proposal("remove", "t1"), proposal("remove", "l1")]
    )
    assert out.headline is None
    assert keys(out) == ["skills", "education", "projects"]


def test_add_child_creates_its_parent_entry_in_profile_order() -> None:
    out = apply_modifications(BASE, P, [proposal("add", "x2a1", "Tableaux de bord construits")])
    entries = section(out, "experience").entries
    assert [e.fact_id for e in entries] == ["x1", "x2"]
    assert entries[1].heading == "Data Analyst — Autre Société"
    assert (entries[1].dates, entries[1].lines[0].fact_ids) == ("2019", ["x2a1"])


def test_add_places_the_fact_at_its_place_in_the_profile() -> None:
    out = apply_modifications(BASE, P, [proposal("add", "c3", "Kubernetes")])
    assert texts(section(out, "skills").items) == ["Python", "Docker", "Kubernetes"]


def test_add_creates_a_missing_section_at_its_usual_place() -> None:
    out = apply_modifications(
        BASE, P, [proposal("add", "k1", "Site"), proposal("add", "s1", "Ingénieure IA passionnée")]
    )
    assert keys(out) == [
        "summary", "skills", "experience", "education", "projects", "languages", "links",
    ]  # fmt: skip
    assert out.sections[0].title == "Profil"


def test_add_entry_level_fact_keeps_the_dates_of_the_profile() -> None:
    out = apply_modifications(BASE, P, [proposal("add", "x2", "Data Analyst — Autre Société")])
    entry = section(out, "experience").entries[1]
    assert (entry.fact_id, entry.dates, entry.lines) == ("x2", "2019", [])


def test_add_title_sets_the_headline_only_when_missing() -> None:
    bare = BASE.model_copy(update={"headline": None})
    assert apply_modifications(bare, P, [proposal("add", "t1", "Ingénieure IA")]).headline == (
        "Ingénieure IA"
    )
    assert apply_modifications(BASE, P, [proposal("add", "t1", "Autre")]).headline == (
        "Ingénieure IA"
    )


def test_apply_ignores_missing_target() -> None:
    accepted = [
        proposal("rewrite", "x2a1", "Texte", ref="a1"),  # fait hors du CV d'origine
        proposal("remove", "c3", ref="a2"),  # idem
        proposal("rewrite", "x9a9", "Texte", ref="a3"),  # inconnu du profil
        proposal("add", "x9a9", "Texte", ref="a4"),
        proposal("add", "c1", "Python", ref="a5"),  # déjà dans le CV
        proposal("rewrite", "x1a1", "  ", ref="a6"),  # texte vide
        proposal("move", None, "skills", section="skills", ref="a7"),  # sur elle-même
        proposal("move", None, "experience", section="links", ref="a8"),  # section absente
        proposal("rewrite", "c2", "Docker 24", ref="a9"),  # la seule appliquée
    ]
    applied = apply_with_report(BASE, P, accepted)
    assert applied.ignored == ["a2", "a1", "a3", "a6", "a4", "a5", "a7", "a8"]
    assert texts(section(applied.content, "skills").items) == ["Python", "Docker 24"]
    assert apply_modifications(BASE, P, accepted) == applied.content


def test_application_order_is_remove_rewrite_add_move() -> None:
    # Retirer avant de réécrire : la réécriture de la ligne retirée est ignorée ; `move` passe en
    # dernier et voit la section créée par `add`.
    accepted = [
        proposal("move", None, "summary", section="education", ref="a4"),
        proposal("add", "s1", "Ingénieure IA passionnée", ref="a3"),
        proposal("rewrite", "c2", "Docker", ref="a2"),
        proposal("remove", "c2", ref="a1"),
    ]
    applied = apply_with_report(BASE, P, accepted)
    assert applied.ignored == ["a2"]
    assert keys(applied.content)[:3] == ["education", "summary", "skills"]
    assert texts(section(applied.content, "skills").items) == ["Python"]


def test_move_puts_the_section_before_the_other() -> None:
    out = apply_modifications(BASE, P, [proposal("move", None, "skills", section="education")])
    assert keys(out) == ["education", "skills", "experience", "projects", "languages"]
