"""Une panne fictive se déclenche en temps virtuel et se vérifie dans le bac."""

import asyncio
import json

import httpx
from fastapi import FastAPI

from app.features.oncall.service.diagnostic import passed
from app.providers.sandbox.base import SandboxJob, SandboxProgress, SandboxResult
from app.providers.sandbox.fake import FakeSandbox

ROOT = "/api/v1/oncall/incidents"
IDE = "/api/v1/ide/sessions"
GOOD = json.dumps(
    {
        "checks": [
            {
                "latency_ms": 180,
                "pending": 0,
                "accepted": size,
                "note": "fictitious routine available",
            }
            for size in (3, 7, 11)
        ]
    }
)


async def opened(client: httpx.AsyncClient, kind: str = "latency", seed: int = 303) -> dict:
    started = await client.post(ROOT, json={"kind": kind, "seed": seed})
    assert started.status_code == 201, started.text
    return started.json()


async def alerted(client: httpx.AsyncClient, root: str) -> dict:
    for _ in range(4):
        updated = await client.post(f"{root}/advance")
        assert updated.status_code == 200, updated.text
        if updated.json()["alerted"]:
            return updated.json()
    raise AssertionError("alerte attendue avant le cinquième pas")


async def test_simulated_alert_and_observations_are_persisted(client: httpx.AsyncClient) -> None:
    begin = await opened(client)
    twin = await opened(client)
    assert begin["minute"] == 0 and begin["alerted"] is False
    assert begin["ide_session_id"] != twin["ide_session_id"]
    root = f"{ROOT}/{begin['id']}"
    incident = await alerted(client, root)
    other = await alerted(client, f"{ROOT}/{twin['id']}")
    assert incident["minute"] == other["minute"] == 2
    assert incident["events"] == other["events"]

    alert = next(event for event in incident["events"] if event["kind"] == "alert")
    location = f"{root}/events/{alert['id']}/observe"
    assert (await client.post(location)).status_code == 200
    assert (await client.post(location)).status_code == 200
    stored = (await client.get(root)).json()
    assert stored["observed_events"] == [alert["id"]]


async def test_technical_result_comes_from_the_bac_and_expires_after_an_edit(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    app.state.providers.sandbox = FakeSandbox({"*": GOOD})
    incident = await opened(client, "queue")
    root = f"{ROOT}/{incident['id']}"
    project = f"{IDE}/{incident['ide_session_id']}"
    draft = (await client.get(project)).json()
    assert "service.py" in draft["files"]
    await alerted(client, root)
    diagnostic = await client.post(f"{root}/diagnostic")
    assert diagnostic.status_code == 202, diagnostic.text
    settled = (await client.get(root)).json()
    assert settled["diagnostic"]["state"] == "passed"

    new_files = {**draft["files"], "service.py": "# correction suivante\n"}
    assert (await client.put(f"{project}/files", json={"files": new_files})).status_code == 200
    assert (await client.get(root)).json()["diagnostic"]["state"] == "stale"
    rejected = await client.post(f"{root}/report", json={"text": "Rapport d’exercice."})
    assert rejected.status_code == 409


async def test_virtual_metrics_recover_after_a_successful_diagnostic(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    app.state.providers.sandbox = FakeSandbox({"*": GOOD})
    incident = await opened(client, "queue")
    root = f"{ROOT}/{incident['id']}"
    raised = await alerted(client, root)
    assert raised["events"][0]["value"] == 0
    assert raised["events"][-1]["value"] > 0
    await client.post(f"{root}/diagnostic")
    assert (await client.get(root)).json()["diagnostic"]["state"] == "passed"
    recovered = (await client.post(f"{root}/advance")).json()
    assert recovered["events"][-1]["value"] == 0


async def test_diagnostic_copies_the_project_and_expires_when_a_helper_changes(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    sandbox = FakeSandbox({"*": GOOD})
    app.state.providers.sandbox = sandbox
    incident = await opened(client)
    root = f"{ROOT}/{incident['id']}"
    project = f"{IDE}/{incident['ide_session_id']}"
    files = (await client.get(project)).json()["files"]
    files["service.py"] = files["service.py"].replace(
        "LATENCY_MS = 880", "from helpers import LATENCY_MS"
    )
    files["helpers.py"] = "LATENCY_MS = 180\n"
    files["diagnostic.py"] = "# Fichier du projet\n"
    assert (await client.put(f"{project}/files", json={"files": files})).is_success
    await alerted(client, root)
    assert (await client.post(f"{root}/diagnostic")).status_code == 202
    [job] = sandbox.jobs
    assert {name: job.files.get(name) for name in files} == files
    assert job.entry not in files
    assert (await client.get(root)).json()["diagnostic"]["state"] == "passed"

    files["helpers.py"] = "LATENCY_MS = 300\n"
    assert (await client.put(f"{project}/files", json={"files": files})).is_success
    assert (await client.get(root)).json()["diagnostic"]["state"] == "stale"


class DelayedSandbox(FakeSandbox):
    completed = False
    unavailable = False

    async def submit(self, job: SandboxJob) -> None:
        if self.unavailable:
            raise OSError("Indisponibilité simulée")
        await super().submit(job)

    async def poll(self, run_id: str, offset: int) -> SandboxProgress:
        if not self.completed:
            return SandboxProgress("", offset, None)
        return await super().poll(run_id, offset)


async def test_concurrent_incidents_share_one_diagnostic_slot(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    sandbox = DelayedSandbox({"*": GOOD})
    app.state.providers.sandbox = sandbox
    incidents = [f"{ROOT}/{(await opened(client))['id']}" for _ in range(2)]
    for incident in incidents:
        await alerted(client, incident)
    starts = [f"{incident}/diagnostic" for incident in incidents]

    replies = await asyncio.gather(*(client.post(path) for path in starts))
    assert sorted(reply.status_code for reply in replies) == [202, 409]
    assert len(sandbox.jobs) == 1
    blocked = replies.index(next(reply for reply in replies if reply.status_code == 409))
    assert replies[blocked].json()["error"]["code"] == "diagnostic_in_progress"

    sandbox.completed = sandbox.unavailable = True
    assert (await client.post(starts[blocked])).status_code == 503
    sandbox.unavailable = False
    assert (await client.post(starts[blocked])).status_code == 202
    assert len(sandbox.jobs) == 2


def test_diagnostic_accepts_one_complete_controller_message() -> None:
    done = SandboxResult(status="done", exit_code=0, duration_ms=1, truncated=False)
    assert passed(SandboxProgress(GOOD, len(GOOD), done))
    additional_output = f"Service démarré\n{GOOD}"
    assert not passed(SandboxProgress(additional_output, len(additional_output), done))
