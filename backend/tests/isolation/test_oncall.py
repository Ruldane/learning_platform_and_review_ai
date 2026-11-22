"""Un incident et ses actions appartiennent à la personne qui le lance."""

from tests.features.oncall.test_incidents import ROOT, alerted, opened
from tests.isolation.conftest import Browser


async def test_other_account_cannot_read_or_change_an_incident(
    google_client_factory: Browser,
) -> None:
    first = await google_client_factory("astreinte-a@example.test")
    other = await google_client_factory("astreinte-b@example.test")
    exercise = await opened(first)
    root = f"{ROOT}/{exercise['id']}"
    current = await alerted(first, root)
    event = current["events"][0]["id"]
    assert (await other.get(ROOT)).json() == []
    assert (await other.get(root)).status_code == 404
    for action in ("advance", f"events/{event}/observe", "diagnostic"):
        assert (await other.post(f"{root}/{action}")).status_code == 404
    denied = await other.post(f"{root}/report", json={"text": "Rapport fictif d’un tiers."})
    assert denied.status_code == 404
    own = await opened(other, "quota")
    assert own["id"] != exercise["id"] and own["ide_session_id"] != exercise["ide_session_id"]
