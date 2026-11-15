"""Le verrou des candidatures de l'utilisatrice (D139) : des créations manuelles identiques
simultanées ne font qu'une fiche, des lectures simultanées n'adoptent une version qu'une fois."""

import asyncio

import httpx
from fastapi import FastAPI

from tests.features.applications.conftest import API, create


async def test_concurrent_identical_creations_make_one_application(
    client: httpx.AsyncClient,
) -> None:
    body = {"company": "Société Fictive", "title": "Développeuse IA"}
    answers = await asyncio.gather(*(create(client, **body) for _ in range(4)))
    codes = sorted(r.status_code for r in answers)
    assert codes == [201, 409, 409, 409]
    assert {r.json()["error"]["code"] for r in answers if r.status_code == 409} == {
        "application_duplicate"
    }
    assert len((await client.get(API)).json()) == 1


async def test_concurrent_creations_from_one_posting_make_one_application(
    client: httpx.AsyncClient, posting: str
) -> None:
    answers = await asyncio.gather(*(create(client, posting_id=posting) for _ in range(4)))
    assert sorted(r.status_code for r in answers) == [201, 409, 409, 409]
    assert {r.json()["error"]["code"] for r in answers if r.status_code == 409} == {
        "application_exists"
    }


async def test_concurrent_reads_adopt_one_application(
    client: httpx.AsyncClient, app: FastAPI, posting: str, ready_version: str
) -> None:
    answers = await asyncio.gather(*(client.get(API) for _ in range(6)))
    assert all(r.status_code == 200 for r in answers)
    assert len((await client.get(API)).json()) == 1
    stats = await asyncio.gather(*(client.get(f"{API}/stats") for _ in range(3)))
    assert all(r.json()["by_status"]["to_apply"] == 1 for r in stats)
