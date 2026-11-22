"""Le terminal utilise le bac et partage ses limites avec les exécutions."""

import httpx
import pytest

from tests.features.ide.conftest import UseSandbox
from tests.features.ide.support import API, new_session

pytestmark = pytest.mark.usefixtures("me")


async def test_terminal_forwards_input_output_and_interruption_to_the_sandbox(
    client: httpx.AsyncClient, use_sandbox: UseSandbox
) -> None:
    fake = use_sandbox({"*": ("Terminal prêt\n", "Une ligne\n", "Fin\n")})
    session = await new_session(client, {"main.py": "print('données fictives')"})
    started = await client.post(f"{API}/sessions/{session['id']}/terminal")
    assert started.status_code == 202, started.text
    terminal = f"{API}/terminals/{started.json()['id']}"
    live = (await client.get(terminal)).json()
    assert live["status"] == "running" and live["output"] == "Terminal prêt\n"
    sent = await client.post(f"{terminal}/input", json={"data": "python main.py\n"})
    assert sent.status_code == 204 and fake.inputs == [(started.json()["id"], b"python main.py\n")]
    assert (await client.delete(terminal)).status_code == 204
    final = (await client.get(terminal, params={"after": live["next_offset"]})).json()
    assert final["status"] == "killed" and final["output"] == ""


async def test_terminal_rejects_overlong_encoded_input_and_hides_old_runs(
    client: httpx.AsyncClient, use_sandbox: UseSandbox
) -> None:
    use_sandbox({"*": ("début", "fin")})
    session = await new_session(client, {"main.py": "print('fictif')"})
    base = f"{API}/sessions/{session['id']}"
    started = await client.post(f"{base}/terminal")
    assert started.status_code == 202
    terminal = f"{API}/terminals/{started.json()['id']}"
    over = await client.post(f"{terminal}/input", json={"data": "é" * 4096})
    assert over.status_code == 422
    assert (await client.get(f"{base}/runs")).json() == []
