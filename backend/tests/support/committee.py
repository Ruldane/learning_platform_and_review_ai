"""Faux port du comité de recrutement (`FakeCommitteeStore`) en mémoire, idempotent par session
comme le contrat (D147). Aucun réseau ni LLM."""

import asyncio
from dataclasses import dataclass, field
from typing import Any

from app.agents.tools.committee_port import CommitteeStore
from app.agents.tools.committee_schema import (
    CommitteeContext,
    PersonaVote,
    Synthesis,
    ats_terms_of,
    cv_plain_text,
)
from app.agents.tools.posting_schema import PostingAnalysis
from scripts.sample_posting import POSTING_TEXT
from tests.support.gap import analysis_data
from tests.support.interviews import default_cv, default_dossier
from tests.support.text_claims import P

RUN_ID = "00000000-0000-4000-8000-0000000000d1"
COMPANY, TITLE = "Société Fictive", "AI Product Engineer"


def default_context(**over: Any) -> CommitteeContext:
    analysis = PostingAnalysis.model_validate(analysis_data())
    cv_text = cv_plain_text(default_cv())
    fields: dict[str, Any] = {
        "cv_text": cv_text,
        "posting_text": POSTING_TEXT,
        "analysis": analysis,
        "dossier": default_dossier(),
        "size": "startup",
        "ats_terms": ats_terms_of(analysis, cv_text),
        "profile": P,
        "company": COMPANY,
        "title": TITLE,
    }
    return CommitteeContext(**(fields | over))


@dataclass
class Saved:
    session_id: str
    votes: list[PersonaVote]
    synthesis: Synthesis


@dataclass
class FakeCommitteeStore:
    ctx: CommitteeContext = field(default_factory=default_context)
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

    async def context(self, user_id: str, run_id: str) -> CommitteeContext:
        self.context_calls += 1
        return self.ctx

    async def save_result(
        self,
        user_id: str,
        session_id: str,
        run_id: str,
        votes: list[PersonaVote],
        synthesis: Synthesis,
    ) -> None:
        self.save_calls += 1
        if session_id not in self.saved:
            self.saved[session_id] = Saved(session_id, votes, synthesis)
            if self.block_after_save:
                await asyncio.Event().wait()


_PORT_CHECK: CommitteeStore = FakeCommitteeStore()  # le faux suit le contrat du port
