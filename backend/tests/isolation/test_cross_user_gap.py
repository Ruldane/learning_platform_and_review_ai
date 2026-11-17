"""Routeur `gap` : l'écart d'une offre n'est lisible que par son propriétaire ; « Ajouter au
planning » ne lance rien pour une offre d'une autre ; les compétences les plus manquantes ne
comptent que les offres de la personne connectée."""

import httpx
from fastapi import FastAPI

from app.db.models.accounts import User
from app.db.models.postings import JobPosting
from tests.sessions_support import act_as
from tests.support.gap import MATCHES, analysis_data

API = "/api/v1"
OTHER = "autre-utilisatrice"


async def _analyzed_posting(app: FastAPI, user_id: str) -> str:
    """Une offre analysée avec son écart, rangée directement en base."""
    async with app.state.session_factory() as db:
        row = JobPosting(
            user_id=user_id,
            source="text",
            text="Offre analysée de la première.",
            text_hash=f"h-{user_id}",
            status="ready",
            title="AI Product Engineer",
            company="Société Fictive",
            analysis=analysis_data(),
            gap={
                "session_id": "s-gap",
                "matches": [{"need": need, "known": known} for need, known in MATCHES.items()],
            },
        )
        db.add(row)
        await db.commit()
        return row.id


async def test_gap_of_another_account_is_invisible(client: httpx.AsyncClient, app: FastAPI) -> None:
    posting = await _analyzed_posting(app, app.state.local_user_id)
    mine = (await client.get(f"{API}/postings/{posting}/gap")).json()
    assert mine["status"] == "ready" and mine["rows"]
    missing = (await client.get(f"{API}/gap/top-missing")).json()
    assert missing  # chez elle, des compétences manquent

    async with app.state.session_factory() as db:
        db.add(User(id=OTHER, user_id=OTHER))
        await db.commit()
    act_as(app, OTHER)
    r = await client.get(f"{API}/postings/{posting}/gap")
    assert (r.status_code, r.json()["error"]["code"]) == (404, "posting_not_found")
    plan = await client.post(f"{API}/postings/{posting}/gap/plan", json={"skills": ["LangGraph"]})
    assert (plan.status_code, plan.json()["error"]["code"]) == (404, "posting_not_found")
    assert (await client.get(f"{API}/gap/top-missing")).json() == []  # aucune offre à elle

    app.dependency_overrides.clear()
    assert (await client.get(f"{API}/gap/top-missing")).json() == missing  # intact chez la première
