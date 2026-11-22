"""Il est impossible de lire une expérience d’un autre compte."""

import httpx
from fastapi import FastAPI

from app.db.models.accounts import User
from app.db.models.paper_lab import PaperLab
from tests.sessions_support import act_as

ROOT = "/api/v1/paper-labs"


async def test_source_course_and_notebook_link_are_isolated(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    owner = app.state.local_user_id
    other = "autre-compte-papier"
    async with app.state.session_factory() as db:
        row = PaperLab(
            user_id=owner,
            url="https://articles.exemple.org/regression",
            title="Cours consacré au compte",
            stage="ready",
            session_id="session-synthetique",
            ide_session_id="projet-synthetique",
        )
        db.add_all([row, User(id=other, user_id=other)])
        await db.commit()
    path = f"{ROOT}/{row.id}"
    assert (await client.get(path)).json()["ide_session_id"] == "projet-synthetique"
    assert len((await client.get(ROOT)).json()) == 1
    act_as(app, other)
    assert (await client.get(path)).status_code == 404
    assert (await client.get(ROOT)).json() == []
