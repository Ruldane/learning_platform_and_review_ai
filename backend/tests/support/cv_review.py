"""Fabriques des tests du validateur des modifications de CV (6.12) : un profil `x1` / `x1a1` /
`c1`…, une analyse d'offre, des propositions ; et le faux port de la revue (`FakeCvReviewStore`,
6.13), en mémoire. Aucun réseau ni LLM."""

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from app.agents.tools.cv_compose import base_content
from app.agents.tools.cv_indicators import AtsCheck, Coverage, Indicators
from app.agents.tools.cv_review_port import (
    AtsUpdate,
    ReviewContext,
    ReviewReport,
    VersionOutcome,
)
from app.agents.tools.cv_schema import (
    CvContent,
    Education,
    Experience,
    Identity,
    Language,
    Line,
    Link,
    MasterProfileData,
    Project,
    SectionKey,
    SkillFact,
    SourcedLine,
    assign_fact_ids,
)
from app.agents.tools.cv_validator import Verdict
from app.agents.tools.posting_schema import Keyword, PostingAnalysis, normalize_term
from app.agents.tools.review_schema import CompanyBrief, Proposal, section_of
from app.core.errors import AppError
from app.db.models.career import VersionStatus
from scripts.sample_posting import POSTING_TEXT
from tests.support.gap import POSTING_ID, analysis_data


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


# --- Faux port de la revue (`FakeCvReviewStore`, 6.13) ----------------------------------------

REVIEW_ID = "00000000-0000-4000-8000-0000000000aa"
ORDER: list[SectionKey] = ["summary", "experience", "skills", "education", "projects", "languages"]


def before() -> Indicators:
    return Indicators(
        coverage=Coverage(covered=3, total=4, percent=75, missing=["LangGraph obligatoire"]),
        checks=[
            AtsCheck(id="selectable_text", passed=True, detail="Le texte se sélectionne."),
            AtsCheck(id="standard_headings", passed=False, detail="1 intitulé n'est pas usuel."),
        ],
    )


@dataclass
class FakeCvReviewStore:
    """En mémoire, idempotent comme le contrat : `save_company` par (clé, session),
    `save_proposals` par (revue, référence), `render_version` par version, `close` par revue."""

    profile: MasterProfileData = field(default_factory=compose_profile)
    analysis: PostingAnalysis | None = field(
        default_factory=lambda: PostingAnalysis.model_validate(analysis_data())
    )
    posting_id: str = POSTING_ID
    posting_text: str = POSTING_TEXT
    posting_urls: list[str] = field(default_factory=lambda: ["https://example.org/offres/1"])
    company: str | None = "Société Fictive"
    company_brief: CompanyBrief | None = None
    company_ats: str | None = None
    base: CvContent | None = None  # par défaut : `base_content(profile, ORDER)`
    ats_updates: list[AtsUpdate] = field(default_factory=list)  # 8.2 : mises à jour du web
    companies: dict[tuple[str, str], tuple[str, list[str], str | None]] = field(
        default_factory=dict
    )
    saved: dict[str, tuple[Proposal, Verdict]] = field(default_factory=dict)
    saved_refs: list[str] = field(default_factory=list)
    gap_terms: list[str] = field(default_factory=list)
    report: ReviewReport | None = None
    save_calls: int = 0
    block_after_save: bool = False
    statuses: dict[str, VersionStatus] = field(default_factory=dict)  # posés par le test
    render_calls: list[str] = field(default_factory=list)
    rendered: list[str] = field(default_factory=list)
    block_after_render: bool = False
    closed: list[str] = field(default_factory=list)

    async def context(self, user_id: str, review_id: str) -> ReviewContext:
        if review_id != REVIEW_ID:
            raise AppError("review_not_found", "Revue introuvable.", 404)
        return ReviewContext(
            review_id=review_id,
            posting_id=self.posting_id,
            analysis=self.analysis,
            posting_text=self.posting_text,
            posting_urls=list(self.posting_urls),
            profile=self.profile,
            base=self.base or base_content(self.profile, ORDER),
            before=before(),
            company=self.company,
            company_brief=self.company_brief,
            company_ats=self.company_ats,
            ats_updates=list(self.ats_updates),
        )

    async def save_company(
        self,
        user_id: str,
        session_id: str,
        name: str,
        brief: CompanyBrief,
        sources: Sequence[str],
        ats: str | None,
    ) -> None:
        self.companies.setdefault((normalize_term(name), session_id), (name, list(sources), ats))
        self.company_brief = brief

    async def save_proposals(
        self,
        user_id: str,
        session_id: str,
        review_id: str,
        items: Sequence[tuple[Proposal, Verdict]],
        gap_terms: Sequence[str],
        report: ReviewReport,
    ) -> int:
        self.save_calls += 1
        for proposal, verdict in items:
            if proposal.ref not in self.saved:
                self.saved[proposal.ref] = (proposal, verdict)
                self.saved_refs.append(proposal.ref)
        self.gap_terms = list(dict.fromkeys([*self.gap_terms, *gap_terms]))
        self.report = self.report or report
        if self.block_after_save:
            await asyncio.Event().wait()
        return len(self.saved)

    async def render_version(self, user_id: str, version_id: str) -> VersionOutcome:
        self.render_calls.append(version_id)
        if version_id not in self.rendered:
            self.rendered.append(version_id)
            if self.block_after_render:
                await asyncio.Event().wait()
        status = self.statuses.get(version_id, "ready")
        pages = 2 if status == "pages_exceeded" else 1
        return VersionOutcome(version_id, status, pages, "CV_Camille_Exemple.pdf", 1)

    async def close(self, user_id: str, review_id: str) -> None:
        if review_id not in self.closed:
            self.closed.append(review_id)

    def accepted_texts(self) -> list[str]:
        """Le texte des modifications rangées `proposed` (verdict `ok`)."""
        return [p.after for p, v in self.saved.values() if v.status == "ok"]

    def status_of(self, ref: str) -> str:
        return "proposed" if self.saved[ref][1].status == "ok" else "to_confirm"
