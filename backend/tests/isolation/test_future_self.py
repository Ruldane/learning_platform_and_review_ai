"""La projection isole simultanément historique, compétences, programme et radar."""

import httpx
import pytest
from fastapi import FastAPI

from app.db.models.accounts import User
from tests.features.future_self.support import API, ROLE, freeze_clock, seed
from tests.sessions_support import act_as


async def test_projection_of_another_account_cannot_read_the_sources(
    client: httpx.AsyncClient, app: FastAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    freeze_clock(monkeypatch)
    refs = await seed(app, app.state.local_user_id)
    before = await client.get(API, params={"role": ROLE})
    assert before.status_code == 200 and before.json()["offer_count"] == 4
    other = "autre-compte-projection"
    async with app.state.session_factory() as db:
        db.add(User(id=other, user_id=other))
        await db.commit()
    act_as(app, other)
    visible = await client.get(API, params={"role": ROLE})
    assert visible.status_code == 200, visible.text
    data = visible.json()
    assert data["sample"] is None and data["program_id"] is None
    assert data["current_percent"] is None and data["observed_weeks"] == 0
    assert data["recommendations"] == []
    assert refs.run_id not in visible.text and refs.lesson_id not in visible.text
    prohibited = await client.get(API, params={"role": ROLE, "program_id": refs.program_id})
    assert (prohibited.status_code, prohibited.json()["error"]["code"]) == (
        404,
        "program_not_found",
    )
    app.dependency_overrides.clear()
    assert (await client.get(API, params={"role": ROLE})).json() == before.json()
