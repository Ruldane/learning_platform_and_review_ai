"""L'entretien garde une seule base de chiffres et un bilan propre au jeu de rôle."""

from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from tests.features.applications.interview_support import ROOT, add_profile, spy
from tests.features.applications.salary_support import (
    ANSWER,
    BODY,
    ROLE,
    SCRIPT,
    ZONE,
    add_salary_run,
    seed_negotiation,
)
from tests.sessions_support import use_test_runtime, wait_status


@pytest.fixture
def scripted_salary(monkeypatch: pytest.MonkeyPatch) -> None:
    use_test_runtime(monkeypatch, SCRIPT)


async def pending(client: httpx.AsyncClient, session_id: str) -> dict[str, Any]:
    shown = await wait_status(client, session_id, "waiting_user")
    prompt: dict[str, Any] = shown["pending_interrupt"]
    return prompt


async def resume(
    client: httpx.AsyncClient, session_id: str, prompt: dict[str, Any], value: object
) -> None:
    accepted = await client.post(
        f"{ROOT}/sessions/{session_id}/resume",
        json={"interrupt_id": prompt["interrupt_id"], "value": value},
    )
    assert accepted.status_code < 300, accepted.text


@pytest.mark.usefixtures("scripted_salary")
async def test_salary_negotiation_uses_scoped_amounts_and_persists_the_simulation(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    sample_id = await seed_negotiation(app)
    started = await client.post(f"{ROOT}/interviews", json=BODY)
    assert started.status_code == 202, started.text
    session_id = started.json()["session_id"]
    own_url = f"{ROOT}/interviews/{started.json()['interview_id']}"
    shown = (await client.get(own_url)).json()
    assert shown["salary"] == {
        "run_id": sample_id,
        "role": ROLE,
        "zone": ZONE,
        "minimum_eur": 50000,
        "maximum_eur": 70000,
        "observations": 2,
    }
    assert shown["salary_outcome"] is None
    first = await pending(client, session_id)
    assert "50 000" in first["question"] and "70 000" in first["question"]
    await add_salary_run(app, app.state.local_user_id, day=19, salaries=["125 k€ brut annuel"])
    await resume(client, session_id, first, {"answers": {"answer": ANSWER}})
    second = await pending(client, session_id)
    assert "70 000" in second["question"] and "99 000" not in second["question"]
    assert "simulation" in second["question"].lower()
    await resume(client, session_id, second, "stop")
    await wait_status(client, session_id, "completed")
    saved = (await client.get(own_url)).json()
    assert saved["salary"] == shown["salary"]
    assert saved["salary_outcome"] == {
        "offer_eur": 70000,
        "remaining_eur": 0,
        "reason": "ceiling_reached",
    }
    assert "99 000" not in str(saved["debrief"])


async def test_salary_negotiation_needs_an_owned_usable_sample(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    launcher = spy(app)
    await add_profile(app)
    await add_salary_run(app, "autre-compte", day=15, salaries=["65 k€ brut annuel"])
    await add_salary_run(
        app, app.state.local_user_id, day=16, salaries=["450 €/jour", "5 000 € net par mois"]
    )
    response = await client.post(f"{ROOT}/interviews", json=BODY)
    assert (response.status_code, response.json()["error"]["code"]) == (409, "radar_salary_missing")
    assert not launcher.started
