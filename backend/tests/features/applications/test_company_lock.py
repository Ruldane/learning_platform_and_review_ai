"""La fiche entreprise (`companies`) est créée par la revue de CV et par le dossier du kit : un seul
verrou par clé d'entreprise (M7), donc une seule ligne, quel que soit l'ordre d'arrivée."""

import asyncio

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select

from app.agents.tools.review_schema import CompanyBrief
from app.db.models.postings import Company
from tests.features.applications.kit_support import COMPANY, SESSION, dossier, sources

pytestmark = pytest.mark.usefixtures("client")


async def test_company_created_once_under_one_lock(
    client: httpx.AsyncClient, app: FastAPI, me: str
) -> None:
    """Deux créations concurrentes (le dossier du kit, la fiche de la revue) : une seule ligne,
    chacune garde ses colonnes."""
    career = app.state.career
    brief = CompanyBrief(summary="Éditeur d'assistants.", values=[], stack=[])
    await asyncio.gather(
        career.kit_store.save_dossier(me, SESSION, COMPANY, dossier(), sources()),
        career.cv_review.save_company(me, "review-session", COMPANY, brief, ["u"], "lever"),
    )
    async with app.state.session_factory() as db:
        [row] = list((await db.execute(select(Company))).scalars())
    assert row.dossier is not None and row.brief is not None and row.ats == "lever"
    assert career.cv.company_locks is career.applications.company_locks
