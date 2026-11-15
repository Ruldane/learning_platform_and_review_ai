"""Matériel des tests des candidatures (D139) : l'app réelle (aucun LLM, aucun réseau), l'horloge
des candidatures figée au 15 novembre 2026, des offres et des versions de CV rangées directement
en base. Données fictives : « Société Fictive », « Autre SA », domaines `example.org`."""

from datetime import UTC, datetime
from itertools import count
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from app.db.models.career import CvReview, CvVersion
from app.db.models.postings import JobPosting
from app.features.postings.service.rules import company_key, posting_url_key

API = "/api/v1/applications"
NOW = datetime(2026, 11, 15, 10, 0, tzinfo=UTC)
_UNIQUE = count(1)


@pytest.fixture
async def client(client: httpx.AsyncClient, app: FastAPI) -> httpx.AsyncClient:
    """Le client de la suite, l'horloge des candidatures figée (15 novembre 2026, 10 h UTC)."""
    app.state.career.applications.now = lambda: NOW
    return client


async def create(client: httpx.AsyncClient, **fields: Any) -> httpx.Response:
    return await client.post(API, json=fields)


async def created_id(client: httpx.AsyncClient, **fields: Any) -> str:
    r = await create(client, **fields)
    assert r.status_code == 201, r.text
    return str(r.json()["application"]["id"])


async def add_posting(app: FastAPI, **over: Any) -> str:
    """Une offre analysée, rangée directement (entreprise et intitulé de l'analyse)."""
    number = next(_UNIQUE)
    company = over.pop("company", "Société Fictive")
    title = over.pop("title", "Développeuse IA")
    url = over.pop("url", f"https://jobs.example.org/offres/{number}")
    user_id = over.pop("user_id", app.state.local_user_id)
    async with app.state.session_factory() as db:
        row = JobPosting(
            user_id=user_id,
            source="url",
            url=url,
            url_norm=posting_url_key(url),
            text=over.pop("text", f"Texte de l'offre fictive numéro {number}."),
            text_hash=f"hash-{number}",
            status="ready",
            company=company,
            company_norm=company_key(company),
            title=title,
            analysis={"title": title, "company": company, "language": "fr"},
            **over,
        )
        db.add(row)
        await db.commit()
        return row.id


async def add_version(app: FastAPI, posting_id: str, number: int = 1, status: str = "ready") -> str:
    """Une version de CV de l'offre (avec sa revue), rangée directement."""
    user_id = app.state.local_user_id
    async with app.state.session_factory() as db:
        review = CvReview(
            user_id=user_id, posting_id=posting_id, template_id="t", profile_version=1,
            status="done",
        )  # fmt: skip
        db.add(review)
        await db.flush()
        version = CvVersion(
            user_id=user_id,
            review_id=review.id,
            posting_id=posting_id,
            template_id="t",
            number=number,
            status=status,
            content={},
            filename="CV_Test.pdf",
            original_page_count=1,
        )
        db.add(version)
        await db.commit()
        return version.id


@pytest.fixture
async def posting(app: FastAPI, client: httpx.AsyncClient) -> str:
    return await add_posting(app)


@pytest.fixture
async def ready_version(app: FastAPI, posting: str) -> str:
    return await add_version(app, posting)
