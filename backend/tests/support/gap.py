"""Faux port de l'analyse d'offre (`FakeGapStore`) en mémoire, idempotent comme le contrat, et les
réponses de l'Analyste pour l'offre fictive de `scripts/sample_posting.py`. Les lignes de l'écart
et le score sont calculés comme le fera `AgentGapStore` (6.6) : niveaux du référentiel,
`learnable` faux → hors périmètre, `match_score`. Comme le contrat (revue 6.5, I2), le
référentiel ne reçoit les besoins de l'offre restés sans rattachement qu'à `save_gap`, après le
rattachement. Aucun réseau ni LLM."""

import asyncio
import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from app.agents.tools.gap_port import (
    AnalysisSaved,
    DuplicateHit,
    GapSaved,
    KnownSkill,
    PostingView,
    SkillMatch,
    gap_result,
    ordered_known,
)
from app.agents.tools.posting_schema import PostingAnalysis
from app.core.errors import AppError
from app.db.models.postings import GapResult, PostingStatus
from app.db.models.skills import SkillLevel
from app.features.gap.service.score import GapAction, GapRow, match_score
from scripts.sample_posting import POSTING_TEXT

POSTING_ID = "00000000-0000-4000-8000-000000000001"
OTHER_ID = "00000000-0000-4000-8000-000000000002"

# Besoins de l'offre : (nom, obligatoire, apprenable) ; et le rattachement attendu.
SKILLS: list[tuple[str, bool, bool]] = [
    ("Python", True, True),
    ("LangGraph", True, True),
    ("RAG", True, True),
    ("Recherche vectorielle", True, True),
    ("Agents conversationnels", True, True),
    ("Évaluation de RAG", True, True),
    ("Développement logiciel", True, True),
    ("Docker", False, True),
    ("Intégration continue", False, True),
    ("Anglais professionnel", False, True),
]
MATCHES: dict[str, str | None] = {
    "Python": "Python",
    "LangGraph": None,
    "RAG": "Génération augmentée par recherche",
    "Recherche vectorielle": "Recherche vectorielle",
    "Agents conversationnels": "Agents LLM",
    "Évaluation de RAG": None,
    "Développement logiciel": "Développement logiciel",
    "Docker": "Docker",
    "Intégration continue": None,
    "Anglais professionnel": None,
}
# Le référentiel de January et ses niveaux : 5 obligatoires acquises, Docker déclaré, 4 absentes
# (2 obligatoires) → 100 × (5 × 2 × 1 + 0,6) / 17 = 62,35 → 62.
LEVELS: dict[str, SkillLevel | None] = {
    "Python": "valide",
    "Génération augmentée par recherche": "valide",
    "Recherche vectorielle": "prouve",
    "Agents LLM": "valide",
    "Développement logiciel": "valide",
    "Docker": "declare",
    "Kubernetes": None,
}


def requirement(text: str, required: bool, *skills: str) -> dict[str, Any]:
    return {"text": text, "required": required, "skills": list(skills)}


def analysis_data(**over: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "is_job_posting": True,
        "title": "AI Product Engineer",
        "company": "Société Fictive",
        "level": "confirme",
        "location": "Lyon",
        "remote": "partiel",
        "language": "fr",
        "requirements": [
            requirement("Python avancé", True, "Python"),
            requirement("LangGraph ou un cadre d'agents équivalent", True, "LangGraph"),
            requirement("RAG : indexation, recherche vectorielle, évaluation", True, "RAG"),
            requirement(
                "3 ans d'expérience en développement logiciel", True, "Développement logiciel"
            ),
            requirement("Docker et intégration continue", False, "Docker"),
            requirement("Anglais professionnel", False),
        ],
        "keywords": [
            {"term": "Python", "variants": []},
            {"term": "LangGraph", "variants": []},
            {"term": "RAG", "variants": ["Retrieval-Augmented Generation"]},
            {"term": "3 ans d'expérience", "variants": []},
        ],
        "eliminatory": [{"kind": "experience_years", "text": "3 ans d'expérience"}],
        "tools": ["LangGraph", "Docker"],
        "skills": [
            {"name": name, "required": required, "domain": None, "learnable": learnable}
            for name, required, learnable in SKILLS
        ],
        "apply_url": None,
    }
    return data | over


def analysis_reply(**over: Any) -> str:
    return json.dumps(analysis_data(**over), ensure_ascii=False)


def not_a_posting_reply() -> str:
    return analysis_reply(
        is_job_posting=False,
        title="Sans titre",
        company=None,
        level="inconnu",
        requirements=[],
        keywords=[],
        eliminatory=[],
        tools=[],
        skills=[],
    )


NEED_REFS = {name: f"n{rank}" for rank, (name, _, _) in enumerate(SKILLS, start=1)}


def known_skills_of(levels: dict[str, SkillLevel | None]) -> list[KnownSkill]:
    return ordered_known([KnownSkill(name, level) for name, level in levels.items()])


def known_refs(levels: dict[str, SkillLevel | None] | None = None) -> dict[str, str]:
    """Nom du référentiel → identifiant montré au modèle (`k1`…, ordre de `ordered_known`)."""
    skills = known_skills_of(LEVELS if levels is None else levels)
    return {skill.name: f"k{rank}" for rank, skill in enumerate(skills, start=1)}


def items_reply(items: list[dict[str, Any]]) -> str:
    return json.dumps({"items": items}, ensure_ascii=False)


def matches_reply(
    matches: dict[str, str | None] | None = None,
    levels: dict[str, SkillLevel | None] | None = None,
) -> str:
    """Réponse du mode `match` par identifiants : `matches` (besoin → nom du référentiel)."""
    refs = known_refs(levels)
    items = [
        {"need": NEED_REFS[need], "known": refs[known] if known else None}
        for need, known in (matches or MATCHES).items()
    ]
    return items_reply(items)


@dataclass
class FakeGapStore:
    texts: dict[str, str] = field(default_factory=lambda: {POSTING_ID: POSTING_TEXT})
    status: dict[str, PostingStatus] = field(default_factory=dict)
    analysis: dict[str, PostingAnalysis] = field(default_factory=dict)
    duplicates: dict[str, list[DuplicateHit]] = field(default_factory=dict)  # posés par le test
    rejected: dict[str, str] = field(default_factory=dict)  # offre → raison
    levels: dict[str, SkillLevel | None] = field(default_factory=lambda: dict(LEVELS))
    weeks: dict[str, int] = field(default_factory=dict)  # compétence → semaine du programme
    gap: dict[str, GapResult] = field(default_factory=dict)
    gaps: dict[str, GapSaved] = field(default_factory=dict)
    save_analysis_calls: int = 0
    save_gap_calls: int = 0
    gap_writes: int = 0
    catalog_added: list[str] = field(default_factory=list)  # besoins entrés au référentiel
    block_after_gap: bool = False
    block_after_analysis: bool = False

    async def posting(self, user_id: str, posting_id: str) -> PostingView:
        if posting_id not in self.texts:
            raise AppError("posting_not_found", "Offre introuvable.", 404)
        status = self.status.get(posting_id, "analyzing")
        found = self.analysis.get(posting_id)
        return PostingView(posting_id, self.texts[posting_id], None, found, status)

    async def save_analysis(
        self, user_id: str, session_id: str, posting_id: str, analysis: PostingAnalysis
    ) -> AnalysisSaved:
        self.save_analysis_calls += 1
        first = posting_id not in self.analysis
        if first:
            self.analysis[posting_id] = analysis
            self.status[posting_id] = "ready"
        hits = self.duplicates.get(posting_id, [])  # rendus aussi quand `first` est faux
        if self.block_after_analysis:
            await asyncio.Event().wait()
        return AnalysisSaved(posting_id, self.analysis[posting_id], hits, first)

    async def reject(self, user_id: str, posting_id: str, reason: str) -> None:
        self.status[posting_id] = "rejected"
        self.rejected.setdefault(posting_id, reason)

    async def known_skills(self, user_id: str) -> list[KnownSkill]:
        return known_skills_of(self.levels)

    def rows(self, posting_id: str, matches: Sequence[SkillMatch]) -> list[GapRow]:
        by_need = {m.need: m.known for m in matches}
        rows: list[GapRow] = []
        for need in self.analysis[posting_id].skills:
            known = by_need.get(need.name)
            level = self.levels.get(known) if known else None
            week = self.weeks.get(known or need.name)
            action: GapAction = "in_program" if week is not None else "to_add"
            if not need.learnable:
                action = "out_of_scope"
            rows.append(GapRow(need.name, need.required, level, action, week))
        return rows

    async def save_gap(
        self, user_id: str, session_id: str, posting_id: str, matches: Sequence[SkillMatch]
    ) -> GapSaved:
        self.save_gap_calls += 1
        if self.gap.get(posting_id, {}).get("session_id") != session_id:
            self.gap_writes += 1
            self.gap[posting_id] = gap_result(session_id, matches)
            rows = self.rows(posting_id, matches)
            absent = [row for row in rows if row.level is None]
            self.gaps[posting_id] = GapSaved(
                match_score(rows), len(rows), len(absent), sum(row.required for row in absent)
            )
            for match in matches:  # après le rattachement : jamais un homonyme sans niveau
                if match.known is None and match.need not in self.levels:
                    self.levels[match.need] = None
                    self.catalog_added.append(match.need)
        if self.block_after_gap:
            await asyncio.Event().wait()
        return self.gaps[posting_id]
