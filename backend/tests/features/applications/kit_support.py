"""Matériel des tests du kit de candidature (D143) : profil validé, fiche avec texte d'offre figé,
pièces rangées par le port réel (`AgentKitStore`), lanceur factice. Données fictives."""

from typing import Any

import httpx
from fastapi import FastAPI
from sqlalchemy import select

from app.agents.tools.kit_schema import CompanyDossier, KitKind, KitStatus, SourceRef
from app.db.models.applications import ApplicationEvent
from app.db.models.career import MasterProfile
from app.features.applications.service.kit_store import AgentKitStore
from tests.features.applications.conftest import API, created_id
from tests.features.lessons.conftest import RecordingLauncher
from tests.support.text_claims import P

POSTING = "Nous cherchons une ingénieure IA pour construire des agents. " * 6
COMPANY = "Société Fictive"
TITLE = "Développeuse IA"
CONTACT = "Alex Recruteur"
SESSION = "11111111-1111-4111-8111-111111111111"
OTHER_SESSION = "22222222-2222-4222-8222-222222222222"
QUESTIONS = [f"Question {chr(97 + rank)} sur l'équipe ?" for rank in range(5)]


def dossier() -> CompanyDossier:
    return CompanyDossier(
        activity="Éditeur d'assistants [1].",
        product="Une plateforme d'agents [1, 2].",
        culture="Équipe réduite [2].",
        interview_process="Trois entretiens [1].",
        questions=QUESTIONS,
    )


def sources(count: int = 3) -> list[SourceRef]:
    return [
        SourceRef(url=f"https://source-{rank}.example.org/page", title=f"Page {rank}")
        for rank in range(1, count + 1)
    ]


async def add_profile(app: FastAPI, user_id: str | None = None) -> None:
    async with app.state.session_factory() as db:
        db.add(
            MasterProfile(
                user_id=user_id or app.state.local_user_id,
                version=1,
                status="validated",
                data=P.model_dump(mode="json"),
                source="january",
            )
        )
        await db.commit()


async def ready_application(
    client: httpx.AsyncClient, app: FastAPI, *, profile: bool = True, **fields: Any
) -> str:
    """Une fiche avec la copie figée du texte d'offre, un contact, et le profil validé."""
    if profile:
        await add_profile(app)
    body: dict[str, Any] = {
        "company": COMPANY,
        "title": TITLE,
        "posting_text": POSTING,
        "contacts": [{"name": CONTACT, "role": "Recruteur"}],
    } | fields
    return await created_id(client, **body)


def spy(app: FastAPI) -> RecordingLauncher:
    current = app.state.career.applications.launcher
    if isinstance(current, RecordingLauncher):
        return current  # déjà posé par le test : un seul lanceur factice par application
    launcher = RecordingLauncher(app.state.session_factory)
    app.state.career.applications.launcher = launcher
    return launcher


def kit_store(app: FastAPI) -> AgentKitStore:
    store = app.state.career.kit_store
    assert isinstance(store, AgentKitStore)
    return store


async def save(
    app: FastAPI,
    application_id: str,
    kind: KitKind,
    *,
    session: str = SESSION,
    status: KitStatus = "ready",
    content: str = "Texte de la pièce.",
    meta: dict[str, Any] | None = None,
) -> str:
    return await kit_store(app).save_piece(
        str(app.state.local_user_id), session, application_id, kind, status, content, meta or {}
    )


async def get_kit(client: httpx.AsyncClient, application_id: str) -> dict[str, Any]:
    r = await client.get(f"{API}/{application_id}/kit")
    assert r.status_code == 200, r.text
    body: dict[str, Any] = r.json()
    return body


def item(kit: dict[str, Any], kind: str) -> dict[str, Any]:
    found: dict[str, Any] = next(i for i in kit["items"] if i["kind"] == kind)
    return found


async def kit_events(app: FastAPI, application_id: str) -> list[ApplicationEvent]:
    async with app.state.session_factory() as db:
        stmt = select(ApplicationEvent).where(
            ApplicationEvent.application_id == application_id, ApplicationEvent.kind == "kit"
        )
        return list((await db.execute(stmt)).scalars())
