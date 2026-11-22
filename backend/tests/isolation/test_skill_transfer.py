from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.skills import evidence
from app.features.skills.service import SkillsService
from tests.isolation.conftest import Browser

API = "/api/v1/skill-transfers"


async def test_owner_can_schedule_one_check_and_other_accounts_cannot_read_it(
    google_client_factory: Browser, db_session: AsyncSession
) -> None:
    owner = await google_client_factory("transfert-a@example.test")
    other = await google_client_factory("transfert-b@example.test")
    now = datetime.now(UTC)
    user_id = (await owner.get("/api/v1/auth/me")).json()["id"]
    skills = SkillsService(db_session, user_id)
    await skills.raise_levels(
        ["Idempotence"], "prouve", evidence("project", "projet-1", "Livraison sans doublons", now)
    )
    skill_id = await skills.skill_id_for("Idempotence")
    await db_session.commit()

    found = await owner.get(f"{API}/proofs", params={"skill_id": skill_id})
    assert found.status_code == 200
    [proof] = found.json()
    assert proof["label"] == "Livraison sans doublons"
    body = {
        "skill_id": skill_id,
        "proof_id": proof["id"],
        "due_on": (now.date() + timedelta(days=2)).isoformat(),
    }
    created = await owner.post(API, json=body)
    assert created.status_code == 201
    assert (await owner.post(API, json=body)).json()["id"] == created.json()["id"]
    assert len((await owner.get(API, params={"skill_id": skill_id})).json()) == 1
    assert (await other.get(f"{API}/proofs", params={"skill_id": skill_id})).json() == []
    assert (await other.get(API, params={"skill_id": skill_id})).json() == []
    assert (await other.post(API, json=body)).status_code == 404

    path = f"{API}/{created.json()['id']}"
    assert (await owner.post(f"{path}/prepare")).status_code == 409
    assert (await other.get(path)).status_code == 404
    assert (await other.post(f"{path}/prepare")).status_code == 404
    assert (await other.post(f"{path}/answer", json={"answer": "Un essai."})).status_code == 404
