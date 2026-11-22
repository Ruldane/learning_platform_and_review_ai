"""Le terminal interactif reste attaché à son compte et à sa séance."""

from fastapi import FastAPI

from app.providers.sandbox.fake import FakeSandbox
from tests.features.ide.support import API
from tests.isolation.conftest import Browser


async def test_terminal_start_input_output_and_cancel_check_ownership(
    google_app: FastAPI, google_client_factory: Browser
) -> None:
    google_app.state.providers.sandbox = FakeSandbox({"*": ("salut", "fin")})
    owner = await google_client_factory("terminal-a@example.test")
    other = await google_client_factory("terminal-b@example.test")
    session = (await owner.post(f"{API}/sessions", json={})).json()
    start = f"{API}/sessions/{session['id']}/terminal"
    assert (await other.post(start)).status_code == 404
    created = await owner.post(start)
    assert created.status_code == 202
    room = f"{API}/terminals/{created.json()['id']}"
    assert (await other.get(room)).status_code == 404
    assert (await other.post(f"{room}/input", json={"data": "texte"})).status_code == 404
    assert (await other.delete(room)).status_code == 404
