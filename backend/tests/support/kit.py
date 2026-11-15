"""Faux port du kit de candidature (`FakeKitStore`) en mémoire, idempotent par `(fiche, pièce,
session)` comme le contrat (D142). Aucun réseau ni LLM."""

import asyncio
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from app.agents.tools.kit_schema import (
    CompanyDossier,
    CvVersionRef,
    KitContext,
    KitKind,
    KitStatus,
    SourceRef,
)
from app.agents.tools.posting_schema import PostingAnalysis
from scripts.sample_posting import POSTING_TEXT
from tests.support.gap import analysis_data
from tests.support.text_claims import P

APPLICATION_ID = "00000000-0000-4000-8000-0000000000b1"
TODAY = date(2026, 11, 15)
COMPANY, TITLE = "Société Fictive", "AI Product Engineer"


def default_context(**over: Any) -> KitContext:
    fields: dict[str, Any] = {
        "application_id": APPLICATION_ID,
        "language": "fr",
        "today": TODAY,
        "posting_text": POSTING_TEXT,
        "analysis": PostingAnalysis.model_validate(analysis_data()),
        "company": COMPANY,
        "title": TITLE,
        "profile": P,
        "cv_version": CvVersionRef(version_id="version-3", number=3),
    }
    return KitContext(**(fields | over))


@dataclass
class Row:
    id: str
    session_id: str
    status: KitStatus
    content: str
    meta: dict[str, Any]


@dataclass
class FakeKitStore:
    ctx: KitContext = field(default_factory=default_context)
    rows: dict[tuple[str, str], Row] = field(default_factory=dict)
    save_calls: int = 0
    block_on_save: int | None = None  # le n-ième appel range la pièce puis se fige (arrêt du back)
    dossiers: list[tuple[str, CompanyDossier, list[SourceRef]]] = field(default_factory=list)
    dossier_sessions: set[str] = field(default_factory=set)
    context_calls: int = 0

    def update(self, **over: Any) -> None:
        self.ctx = self.ctx.model_copy(update=over)

    def piece(self, kind: KitKind) -> Row:
        return self.rows[(self.ctx.application_id, kind)]

    @property
    def kinds(self) -> set[str]:
        return {kind for _, kind in self.rows}

    async def context(self, user_id: str, application_id: str) -> KitContext:
        self.context_calls += 1
        return self.ctx

    async def save_piece(
        self,
        user_id: str,
        session_id: str,
        application_id: str,
        kind: KitKind,
        status: KitStatus,
        content: str,
        meta: dict[str, Any],
    ) -> str:
        self.save_calls += 1
        key = (application_id, kind)
        row = self.rows.get(key)
        if row is None:
            row = Row(
                f"piece-{len(self.rows) + 1}".ljust(36, "0"), session_id, status, content, meta
            )
            self.rows[key] = row
        elif row.session_id != session_id:
            self.rows[key] = Row(row.id, session_id, status, content, meta)
        if self.block_on_save is not None and self.save_calls == self.block_on_save:
            await asyncio.Event().wait()
        return self.rows[key].id

    async def save_dossier(
        self,
        user_id: str,
        session_id: str,
        company: str,
        dossier: CompanyDossier,
        sources: list[SourceRef],
    ) -> None:
        if session_id not in self.dossier_sessions:
            self.dossier_sessions.add(session_id)
            self.dossiers.append((company, dossier, sources))
