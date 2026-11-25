"""Matériel des tests des entretiens blancs (D146) : profil validé, fiche, lanceur factice, offres
et dossier rangés directement, résultat de parcours (échanges, débrief) rangé par le port réel
(`AgentInterviewStore`). Données fictives."""

from typing import Any

import httpx
from fastapi import FastAPI
from sqlalchemy import select

from app.agents.tools.interview_schema import Debrief, Exchange, ExpectedPoints
from app.agents.tools.study_schema import CardDraft
from app.db.models.applications import Application, Interview
from app.db.models.career import CvVersion
from app.db.models.postings import Company, JobPosting
from app.features.applications.service.interview_store import AgentInterviewStore
from app.features.applications.service.kit_store import company_name_key
from tests.features.applications.conftest import NOW, add_posting
from tests.features.applications.kit_support import (
    COMPANY,
    add_profile,
    dossier,
    ready_application,
    sources,
    spy,
)
from tests.support.gap import analysis_data
from tests.support.interviews import default_cv

ROOT = "/api/v1"
BODY = {"mode": "behavioral", "duration_min": 30, "language": "fr"}
SECRET_ANSWER = "Réponse ultra secrète sur mon dernier projet"
SECRET_QUESTION = "Question ultra secrète sur la rupture ?"

__all__ = [
    "BODY",
    "COMPANY",
    "NOW",
    "ROOT",
    "SECRET_ANSWER",
    "SECRET_QUESTION",
    "add_posting",
    "add_profile",
    "dossier",
    "ready_application",
    "sources",
    "spy",
]


def interview_store(app: FastAPI) -> AgentInterviewStore:
    store = app.state.career.interview_store
    assert isinstance(store, AgentInterviewStore)
    return store


def exchange(index: int = 0, note: int = 2, **over: Any) -> Exchange:
    fields: dict[str, Any] = {
        "index": index,
        "question": f"Question {index} sur ton dernier projet ?",
        "criterion": "clarity",
        "source": "general",
        "answer": f"Ma réponse numéro {index}.",
        "note": note,
    }
    return Exchange(**(fields | over))


def debrief(missed: list[int] | None = None, **over: Any) -> Debrief:
    missed = [0] if missed is None else missed
    fields: dict[str, Any] = {
        "scores": {"clarity": 3, "structure": 2, "technical_depth": 4, "role_fit": 3},
        "strengths": ["Exemples concrets.", "Ton posé.", "Bonne écoute."],
        "fixes": ["Annoncer le plan.", "Chiffrer l'impact.", "Conclure plus net."],
        "weakest_index": 0,
        "improved_answer": "Voici comment répondre plus nettement à cette question.",
        "missed": missed,
        "expected": [
            ExpectedPoints(
                index=index, points=[f"Point attendu {index}a", f"Point attendu {index}b"]
            )
            for index in missed
        ],
    }
    return Debrief(**(fields | over))


def card(number: int = 1) -> CardDraft:
    return CardDraft(
        front=f"Comment répondre à la question {number} ?",
        back=f"- Point {number}a\n- Point {number}b",
    )


async def launch(client: httpx.AsyncClient, application_id: str, **over: Any) -> dict[str, str]:
    r = await client.post(f"{ROOT}/applications/{application_id}/interviews", json=BODY | over)
    assert r.status_code == 202, r.text
    out: dict[str, str] = r.json()
    return out


async def running_application(
    client: httpx.AsyncClient, app: FastAPI
) -> tuple[str, dict[str, str]]:
    """Une fiche prête et un entretien lancé (lanceur factice) : `(fiche, départ)`."""
    spy(app)
    application_id = await ready_application(client, app)
    return application_id, await launch(client, application_id)


async def save_done(
    app: FastAPI, started: dict[str, str], *, cards: list[CardDraft] | None = None, **over: Any
) -> None:
    await interview_store(app).save_result(
        str(app.state.local_user_id),
        started["session_id"],
        started["interview_id"],
        over.pop("exchanges", [exchange(0, 2), exchange(1, 4)]),
        over.pop("debrief", debrief()),
        over.pop("flags", []),
        [card()] if cards is None else cards,
    )


async def interview_row(app: FastAPI, interview_id: str) -> Interview:
    async with app.state.session_factory() as db:
        row = (await db.execute(select(Interview).where(Interview.id == interview_id))).scalar_one()
        db.expunge(row)
        return row


async def store_dossier(app: FastAPI, company: str, *, at: Any) -> None:
    async with app.state.session_factory() as db:
        db.add(
            Company(
                user_id=app.state.local_user_id,
                name=company,
                name_norm=company_name_key(company),
                dossier={**dossier().model_dump(mode="json"), "session_id": "s"},
                dossier_sources=[s.model_dump(mode="json") for s in sources()],
                dossier_at=at,
            )
        )
        await db.commit()


async def set_gap(app: FastAPI, posting_id: str, matches: list[dict[str, Any]]) -> None:
    async with app.state.session_factory() as db:
        row = (await db.execute(select(JobPosting).where(JobPosting.id == posting_id))).scalar_one()
        row.gap = {"session_id": "g", "matches": matches}
        row.analysis = analysis_data()  # une analyse complète de l'offre
        await db.commit()


async def set_version_content(app: FastAPI, version_id: str, headline: str) -> None:
    """Le CV de la version : un contenu valide dont seul le titre change."""
    async with app.state.session_factory() as db:
        row = (await db.execute(select(CvVersion).where(CvVersion.id == version_id))).scalar_one()
        row.content = default_cv().model_copy(update={"headline": headline}).model_dump(mode="json")
        await db.commit()


async def send_version(app: FastAPI, application_id: str, version_id: str) -> None:
    """La version de CV envoyée avec la fiche (`cv_version_id`)."""
    async with app.state.session_factory() as db:
        row = (
            await db.execute(select(Application).where(Application.id == application_id))
        ).scalar_one()
        row.cv_version_id = version_id
        await db.commit()
