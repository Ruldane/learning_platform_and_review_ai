"""Les commandes d'appairage ne traversent jamais un compte connecté."""

from tests.features.mcp.test_relay_pairing import EXCHANGE, HOST, PAIRING, ROOT, STATUS, start
from tests.isolation.conftest import Browser


async def test_relay_pairing_belongs_to_the_account_that_created_the_code(
    google_client_factory: Browser,
) -> None:
    first = await google_client_factory("un@example.test")
    other = await google_client_factory("deux@example.test")
    await first.put(f"{ROOT}/settings", json={"enabled": True})
    code = await start(first)
    assert (await other.get(STATUS)).json()["state"] == "unpaired"
    assert (await other.delete(PAIRING)).status_code == 204
    assert (await other.post(EXCHANGE, json={"code": code}, headers=HOST)).status_code == 201
    assert (await other.get(STATUS)).json()["state"] == "unpaired"
    assert (await other.get(f"{ROOT}/tokens")).json() == []
    assert (await first.get(STATUS)).json()["state"] == "paired"
