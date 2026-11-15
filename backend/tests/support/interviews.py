"""Faux port de l'entretien blanc (`FakeInterviewStore`) en mémoire, idempotent par session comme le
contrat (D145). Aucun réseau ni LLM."""

import asyncio
from dataclasses import dataclass, field
from typing import Any

from app.agents.tools.cv_schema import CvContent, CvEntry, CvLine, CvSection
from app.agents.tools.interview_schema import Debrief, Exchange, InterviewContext
from app.agents.tools.kit_schema import CompanyDossier
from app.agents.tools.posting_schema import PostingAnalysis
from app.agents.tools.study_schema import CardDraft
from scripts.sample_posting import POSTING_TEXT
from tests.support.gap import analysis_data
from tests.support.text_claims import P

INTERVIEW_ID = "00000000-0000-4000-8000-0000000000c1"
COMPANY, TITLE = "Société Fictive", "AI Product Engineer"
GAP = "Recherche vectorielle : jamais pratiquée en production"
DOSSIER_NOTE = "Plateforme d'agents conversationnels pour le support client"


def default_cv() -> CvContent:
    entry = CvEntry(
        heading="AI Engineer",
        subheading="Société Fictive",
        dates="2021-03 → 2024-09",
        lines=[CvLine(text="Réduit de 30 % le temps de traitement avec Python", fact_ids=["x1a1"])],
    )
    return CvContent(
        name="Camille Exemple",
        headline="AI Engineer",
        sections=[CvSection(key="experience", title="Expérience", entries=[entry])],
    )


def default_dossier() -> CompanyDossier:
    return CompanyDossier(
        activity=DOSSIER_NOTE,
        product="Un assistant documentaire",
        stack=["Python", "Docker"],
        culture="Équipe réduite, décisions rapides",
        interview_process="Trois entretiens, dont un technique",
        questions=[f"Question {n} sur l'équipe ?" for n in range(5)],
    )


def default_context(**over: Any) -> InterviewContext:
    fields: dict[str, Any] = {
        "mode": "behavioral",
        "duration_min": 15,
        "language": "fr",
        "role": TITLE,
        "posting_text": POSTING_TEXT,
        "analysis": PostingAnalysis.model_validate(analysis_data()),
        "dossier": default_dossier(),
        "cv_content": default_cv(),
        "gaps": [GAP],
        "profile": P,
    }
    return InterviewContext(**(fields | over))


@dataclass
class Saved:
    session_id: str
    exchanges: list[Exchange]
    debrief: Debrief | None
    flags: list[str]
    cards: list[CardDraft]


@dataclass
class FakeInterviewStore:
    ctx: InterviewContext = field(default_factory=default_context)
    context_calls: int = 0
    save_calls: int = 0
    block_after_save: bool = False  # le premier appel range l'issue puis se fige (arrêt du back)
    saved: dict[str, Saved] = field(default_factory=dict)  # par session, comme le contrat

    def update(self, **over: Any) -> None:
        self.ctx = self.ctx.model_copy(update=over)

    @property
    def only(self) -> Saved:
        [saved] = self.saved.values()
        return saved

    async def context(self, user_id: str, interview_id: str) -> InterviewContext:
        self.context_calls += 1
        return self.ctx

    async def save_result(
        self,
        user_id: str,
        session_id: str,
        interview_id: str,
        exchanges: list[Exchange],
        debrief: Debrief | None,
        flags: list[str],
        cards: list[CardDraft],
    ) -> None:
        self.save_calls += 1
        if session_id not in self.saved:
            self.saved[session_id] = Saved(session_id, exchanges, debrief, flags, cards)
            if self.block_after_save:
                await asyncio.Event().wait()
