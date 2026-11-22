"""Les cookies du compte et les jetons du relais gardent des périmètres indépendants."""

from tests.features.brain.test_sync import (
    BRAIN,
    CONFIGURED_PATH,
    FIRST,
    SYNC,
    auth,
    configure,
    upload,
)
from tests.isolation.conftest import Browser


async def test_sync_token_is_scoped_rotated_and_receives_no_stale_folder_writes(
    google_client_factory: Browser,
) -> None:
    owner = await google_client_factory("january@example.com")
    other = await google_client_factory("autre@example.com")
    folder, token = await configure(owner)
    assert (await owner.get(SYNC)).status_code == 401
    status = await owner.get(f"{BRAIN}/status")
    assert CONFIGURED_PATH not in status.text and "path" not in status.json()[0]
    assert (await other.get(f"{BRAIN}/folders")).json() == []
    assert (await other.get(f"{BRAIN}/status")).json() == []
    foreign = await other.post(f"{BRAIN}/sync-token")
    other_token = foreign.json()["token"]
    path = f"{BRAIN}/folders/{folder['id']}"
    assert (await other.patch(path, json={"paused": True})).status_code == 404
    assert (await upload(other, folder, other_token, FIRST)).status_code == 404
    paused = await owner.patch(path, json={"paused": True})
    assert paused.json()["revision"] == 2
    assert (await upload(owner, folder, token, FIRST)).json()["error"][
        "code"
    ] == "brain_revision_conflict"
    assert (await upload(owner, paused.json(), token, FIRST)).json()["error"][
        "code"
    ] == "brain_folder_paused"
    rotated = await owner.post(f"{BRAIN}/sync-token")
    assert rotated.json()["token"] != token
    assert (await owner.get(SYNC, headers=auth(token))).status_code == 401
