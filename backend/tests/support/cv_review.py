"""Fabriques des tests du validateur des modifications de CV (6.12) : un profil `x1` / `x1a1` /
`c1`…, une analyse d'offre, des propositions."""

from typing import Any

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
)
from app.agents.tools.posting_schema import Keyword, PostingAnalysis
from app.agents.tools.review_schema import Proposal, section_of


def profile(
    line: str = "Réalisation", role: str = "AI Engineer", skills: list[str] | None = None, **kw: Any
) -> MasterProfileData:
    """Un profil : une expérience `x1` (rôle `role`) et sa réalisation `x1a1` (`line`), des
    compétences `c1`…, tous venus du CV."""
    return assign_fact_ids(
        MasterProfileData(
            identity=Identity(name="Camille Exemple"),
            experiences=[
                Experience(
                    role=role,
                    company="Société Fictive",
                    achievements=[Line(text=line)],
                    sources=["cv"],
                )
            ],
            skills=[SkillFact(name=name, sources=["cv"]) for name in skills or []],
            **kw,
        )
    )


def analysis(**kwargs: Any) -> PostingAnalysis:
    fields: dict[str, Any] = {
        "is_job_posting": True,
        "title": "Data Scientist (H/F)",
        "level": "confirme",
        "language": "fr",
    } | kwargs
    fields["keywords"] = [Keyword(term=term) for term in fields.get("keywords", [])]
    return PostingAnalysis(**fields)


A = analysis()


def proposal(action: str, target: str | None, after: str, **kw: Any) -> Proposal:
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


def rewrite(target: str, after: str, **kw: Any) -> Proposal:
    return proposal("rewrite", target, after, **kw)


def add(target: str, after: str, **kw: Any) -> Proposal:
    return proposal("add", target, after, **kw)


def _compose_experiences() -> list[Experience]:
    return [
        Experience(
            role="AI Engineer",
            company="Société Fictive",
            location="Paris",
            start="2021-03",
            end="2023-06",
            achievements=[
                Line(text="Réduit les coûts de 30 %"),
                Line(text="Anime l'équipe"),
            ],
            sources=["cv"],
        ),
        Experience(
            role="Data Analyst",
            company="Autre Société",
            start="2019",
            achievements=[Line(text="Construit des tableaux de bord")],
            sources=["linkedin"],
        ),
    ]


def compose_profile() -> MasterProfileData:
    """x1 (CV) et x2 (LinkedIn) ; f1 ; c1 Python, c2 Docker (CV), c3 Kubernetes (note) ; p1 ;
    l1 ; k1 (LinkedIn) ; titre du CV, résumé de LinkedIn."""
    return assign_fact_ids(
        MasterProfileData(
            identity=Identity(
                name="Camille Exemple", email="camille.exemple@example.org", location="Lyon"
            ),
            title=SourcedLine(text="Ingénieure IA", sources=["cv"]),
            summary=SourcedLine(text="Ingénieure IA passionnée", sources=["linkedin"]),
            experiences=_compose_experiences(),
            education=[
                Education(
                    degree="Master",
                    school="École Fictive",
                    details=[Line(text="Mention")],
                    sources=["cv"],
                )
            ],
            skills=[
                SkillFact(name="Python", sources=["cv"]),
                SkillFact(name="Docker", sources=["cv"]),
                SkillFact(name="Kubernetes", sources=["note"]),
            ],
            projects=[
                Project(
                    name="Projet Aurore",
                    description="Assistant interne",
                    achievements=[Line(text="Adopté par 40 personnes")],
                    sources=["cv"],
                )
            ],
            languages=[Language(name="Français", level="natif", sources=["cv"])],
            links=[Link(label="Site", url="https://example.org", sources=["linkedin"])],
        )
    )
