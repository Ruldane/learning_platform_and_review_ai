from tests.isolation.conftest import Browser

PREFERENCES = "/api/v1/lab/preferences"


async def test_lab_preferences_belong_to_one_account(google_client_factory: Browser) -> None:
    owner = await google_client_factory("january@example.com")
    other = await google_client_factory("autre@example.com")
    assert (await owner.get(PREFERENCES)).json() == {"pinned": [], "tour": "pending"}
    update = await owner.patch(PREFERENCES, json={"pinned": ["oncall"], "tour": "disabled"})
    assert update.json() == {"pinned": ["oncall"], "tour": "disabled"}
    assert (await other.get(PREFERENCES)).json() == {"pinned": [], "tour": "pending"}
    assert (await owner.patch(PREFERENCES, json={"pinned": ["settings"]})).status_code == 422
    assert (await owner.patch(PREFERENCES, json={"tour": "done"})).json() == {
        "pinned": ["oncall"],
        "tour": "done",
    }
