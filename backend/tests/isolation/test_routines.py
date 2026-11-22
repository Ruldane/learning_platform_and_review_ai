from uuid import uuid4

from tests.isolation.conftest import Browser


async def test_routines_are_private(google_client_factory: Browser) -> None:
    owner = await google_client_factory("routine-a@example.test")
    other = await google_client_factory("routine-b@example.test")
    base = "/api/v1/routines"
    created = await owner.post(base, json={"action": "due_reviews", "local_time": "08:00"})
    assert created.status_code == 201
    path = f"{base}/{created.json()['id']}"
    assert (await other.get(base)).json() == []
    assert (await other.patch(path, json={"enabled": False})).status_code == 404
    assert (await other.get(f"{path}/executions")).status_code == 404
    receipt = {"receipt": str(uuid4())}
    assert (await other.post(f"{path}/executions", json=receipt)).status_code == 404
    assert (await owner.post(f"{path}/executions", json=receipt)).status_code == 201
