"""Matériel des tests du comité de recrutement (D147) : profil validé, offre analysée, version de CV
prête avec son contenu, lanceur factice, issue de parcours rangée par le port réel
(`AgentCommitteeStore`). Données fictives."""

from datetime import datetime
from typing import Any

import httpx
from fastapi import FastAPI
from sqlalchemy import select

from app.agents.tools.committee_schema import (
    PERSONAS,
    Change,
    PersonaVote,
    RankedObjection,
    Synthesis,
)
from app.db.models.applications import ApplicationEvent, CommitteeRun
from app.db.models.postings import Company
from app.features.applications.service.committee_store import AgentCommitteeStore
from app.features.applications.service.kit_store import company_name_key
from tests.features.applications.conftest import NOW, add_posting, add_version
from tests.features.applications.interview_support import set_gap, set_version_content
from tests.features.applications.kit_support import COMPANY, add_profile, dossier, sources, spy

ROOT = "/api/v1"
UNKNOWN = "00000000-0000-4000-8000-000000000000"
SESSION = "11111111-1111-4111-8111-111111111111"

__all__ = [
    "COMPANY",
    "NOW",
    "ROOT",
    "SESSION",
    "UNKNOWN",
    "add_profile",
    "committee_store",
    "launch",
    "ready_committee",
    "run_row",
    "save_done",
    "spy",
    "synthesis_of",
    "votes_of",
]


def committee_store(app: FastAPI) -> AgentCommitteeStore:
    store = app.state.career.committee_store
    assert isinstance(store, AgentCommitteeStore)
    return store


def votes_of(
    *answers: str, objection: str = "Aucun mot clé LangGraph dans le CV"
) -> list[PersonaVote]:
    """Quatre votes, dans l'ordre des personas (`answers` : « oui », « non » ou « peut_etre »)."""
    return [
        PersonaVote(
            persona=persona,
            vote=answer,  # type: ignore[arg-type]
            objection=objection,
            reason=f"Raison de {persona}.",
        )
        for persona, answer in zip(PERSONAS, answers, strict=True)
    ]


def synthesis_of(verdict: str = "yes", *objections: str, needs_skill: bool = False) -> Synthesis:
    texts = objections or ("Aucun mot clé LangGraph dans le CV", "Pas d'agent en production")
    return Synthesis(
        verdict=verdict,  # type: ignore[arg-type]
        objections=[RankedObjection(text=text, personas=["manager"]) for text in texts],
        changes=[
            Change(text=f"Changement {n}", persona="recruiter", fact_ids=["x1a1"]) for n in range(2)
        ]
        + [
            Change(
                text="À acquérir : LangGraph.",
                persona="ats_reader",
                needs_skill=needs_skill,
                terms=["LangGraph"] if needs_skill else [],
            )
        ],
    )


async def ready_committee(
    client: httpx.AsyncClient,
    app: FastAPI,
    *,
    profile: bool = True,
    fiche: bool = True,
    company: str = COMPANY,
) -> tuple[str, str]:
    """Une offre analysée, une version de CV prête avec son contenu, le profil validé et (par
    défaut) la fiche de l'offre ; `(offre, version)`. Lanceur factice posé."""
    spy(app)
    if profile:
        await add_profile(app)
    posting = await add_posting(app, company=company, text="Offre : agents Python et LangGraph.")
    await set_gap(app, posting, [])  # une analyse complète de l'offre
    version = await add_version(app, posting)
    await set_version_content(app, version, "AI Engineer Python")
    if fiche:
        r = await client.post(
            f"{ROOT}/applications",
            json={"company": company, "title": "Poste", "posting_id": posting},
        )
        assert r.status_code == 201, r.text
    return posting, version


async def launch(client: httpx.AsyncClient, version_id: str) -> dict[str, str]:
    r = await client.post(f"{ROOT}/committee", json={"cv_version_id": version_id})
    assert r.status_code == 202, r.text
    out: dict[str, str] = r.json()
    return out


async def save_done(
    app: FastAPI,
    started: dict[str, str],
    votes: list[PersonaVote],
    synthesis: Synthesis,
) -> None:
    await committee_store(app).save_result(
        str(app.state.local_user_id), started["session_id"], started["run_id"], votes, synthesis
    )


async def run_row(app: FastAPI, run_id: str) -> CommitteeRun:
    async with app.state.session_factory() as db:
        row = (await db.execute(select(CommitteeRun).where(CommitteeRun.id == run_id))).scalar_one()
        db.expunge(row)
        return row


async def committee_events(app: FastAPI, application_id: str) -> list[ApplicationEvent]:
    async with app.state.session_factory() as db:
        stmt = select(ApplicationEvent).where(
            ApplicationEvent.application_id == application_id,
            ApplicationEvent.kind == "committee",
        )
        return list((await db.execute(stmt)).scalars())


async def store_company(app: FastAPI, company: str, size: str, *, at: datetime) -> None:
    """Le dossier de l'entreprise, de la taille donnée, rangé directement."""
    data: dict[str, Any] = dossier().model_dump(mode="json") | {"size": size, "session_id": "s"}
    async with app.state.session_factory() as db:
        db.add(
            Company(
                user_id=app.state.local_user_id,
                name=company,
                name_norm=company_name_key(company),
                dossier=data,
                dossier_sources=[s.model_dump(mode="json") for s in sources()],
                dossier_at=at,
            )
        )
        await db.commit()
