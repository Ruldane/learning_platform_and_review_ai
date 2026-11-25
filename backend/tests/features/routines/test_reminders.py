from datetime import UTC, date, datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import httpx
from fastapi import FastAPI

from app.core.skills import evidence
from app.db.models.dated_commitments import DatedCommitment
from app.db.models.missions import Mission
from app.db.models.skill_transfer import SkillTransfer
from app.features.skills.service import SkillsService


async def test_mission_and_transfer_reminders_have_independent_rules(
    client: httpx.AsyncClient,
    app: FastAPI,
) -> None:
    await _seed_deadlines(app)
    list_path = "/api/v1/routines"
    expected = {"due_reviews": 0, "due_transfers": 1, "missions_ending": 1, "due_commitments": 1}
    for action, count in expected.items():
        response = await client.post(list_path, json={"action": action, "local_time": "09:00"})
        assert response.status_code == 201, response.text
        item = response.json()
        history = f"{list_path}/{item['id']}/executions"
        result = await client.post(history, json={"receipt": str(uuid4())})
        assert result.status_code == 201 and result.json()["result_count"] == count
        if action == "due_commitments":
            notice = result.json()["notices"][0]
            assert (notice["title"], notice["delta"], notice["unit"]) == (
                "Bilan privé",
                "-3",
                "min",
            )
            assert (await client.get(history)).json() == [result.json()]
    assert {item["action"] for item in (await client.get(list_path)).json()} == {
        "due_reviews",
        "due_transfers",
        "missions_ending",
        "due_commitments",
    }


async def _seed_deadlines(app: FastAPI) -> None:
    owner = app.state.local_user_id
    now = datetime.now(UTC)
    today = now.astimezone(ZoneInfo("Europe/Paris")).date()
    async with app.state.session_factory() as db:
        skills = SkillsService(db, owner)
        await skills.raise_levels(
            ["Transactions"], "proven", evidence("project", "sample", "Test", now)
        )
        skill = await skills.skill_id_for("Transactions")
        assert skill is not None
        db.add(
            SkillTransfer(
                user_id=owner,
                skill_id=skill,
                proof_id="sample",
                proof={},
                due_on=date(2020, 1, 1),
                stage="scheduled",
            )
        )
        db.add(
            Mission(
                user_id=owner,
                posting_id="fictive",
                deadline_at=now + timedelta(hours=3),
                revision=0,
                criteria=[],
            )
        )
        db.add(
            DatedCommitment(
                user_id=owner,
                request_id=str(uuid4()),
                title="Bilan privé",
                version="V1",
                intention="Se rapprocher de la cible.",
                indicator="Durée",
                unit="min",
                target="20",
                observed="17",
                due_on=today,
                reviewed_on=today,
                reviewed_at=now,
            )
        )
        await db.commit()
