"""Matériel des tests de l'IDE : des appels de l'API et des états lus en base."""

from typing import Any

import httpx
from fastapi import FastAPI
from sqlalchemy import select

from app.db.models.ide import IdeRun, IdeSession

API = "/api/v1/ide"
FILES = {"main.py": "print('bonjour')\n", "test_main.py": "def test_ok():\n    assert True\n"}
TRACE = (
    "Traceback (most recent call last):\n"
    '  File "/work/9c1/main.py", line 7, in <module>\n'
    "    print(f(0))\n"
    '  File "/work/9c1/main.py", line 3, in f\n'
    "    return 1 / n\n"
    "ZeroDivisionError: division by zero\n"
)


def code(response: httpx.Response) -> str:
    found: str = response.json()["error"]["code"]
    return found


async def new_session(
    client: httpx.AsyncClient, files: dict[str, str] | None = None, **exercise: Any
) -> dict[str, Any]:
    """Une séance : libre (fichiers posés par `PUT`) ou sur un exercice (champs de `exercise`)."""
    if exercise:
        body = {"title": "Un exercice", "statement": "Écris une fonction.", **exercise}
        body["files"] = files or FILES
        made = await client.post(f"{API}/exercises", json=body)
        assert made.status_code == 201, made.text
        opened = await client.post(f"{API}/sessions", json={"exercise_id": made.json()["id"]})
    else:
        opened = await client.post(f"{API}/sessions", json={})
    assert opened.status_code == 201, opened.text
    session: dict[str, Any] = opened.json()
    if files is not None and not exercise:
        put = await client.put(f"{API}/sessions/{session['id']}/files", json={"files": files})
        assert put.status_code == 200, put.text
        session = put.json()
    return session


async def start_run(
    client: httpx.AsyncClient, session_id: str, kind: str = "run"
) -> httpx.Response:
    return await client.post(f"{API}/sessions/{session_id}/runs", json={"kind": kind})


async def run_row(app: FastAPI, run_id: str) -> IdeRun:
    async with app.state.session_factory() as db:
        row = (await db.execute(select(IdeRun).where(IdeRun.id == run_id))).scalar_one()
        return row


async def session_row(app: FastAPI, session_id: str) -> IdeSession:
    async with app.state.session_factory() as db:
        row = (await db.execute(select(IdeSession).where(IdeSession.id == session_id))).scalar_one()
        return row
