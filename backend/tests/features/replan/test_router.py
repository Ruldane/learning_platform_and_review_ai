"""Routes de la replanification (D106) : lancement par un message de January (409 si brouillon
ou déjà ouverte), historique des versions avec leur statut, isolation des utilisateurs, 422 sans
recopie de la saisie, et `POST /sessions` qui renvoie `replan` à sa route."""

from dataclasses import dataclass

import httpx
import pytest
from fastapi import FastAPI

from app.agents.tools.replan_port import ReplanDraft
from app.features.program.service.runtime import ProgramRuntime
from app.features.replan.service.runtime import ReplanRuntime
from app.features.replan.service.store import AgentReplanStore
from tests.features.lessons.conftest import RecordingLauncher
from tests.features.replan.conftest import NOW, OTHER, drafted, validated, versions

API = "/api/v1"


@dataclass
class Routes:
    app: FastAPI
    user_id: str
    launcher: RecordingLauncher

    @property
    def rt(self) -> ReplanRuntime:
        runtime: ReplanRuntime = self.app.state.replan
        return runtime

    @property
    def program(self) -> ProgramRuntime:
        """Le programme de l'app, sans production des leçons (aucune session lancée)."""
        return ProgramRuntime(self.app.state.session_factory, self.app.state.memory)


@pytest.fixture
async def routes(client: httpx.AsyncClient, app: FastAPI) -> Routes:
    launcher = RecordingLauncher(app.state.session_factory)
    app.state.replan.launcher = launcher
    app.state.replan.now = lambda: NOW
    return Routes(app, app.state.local_user_id, launcher)


async def test_start_replan_conflicts_when_open(client: httpx.AsyncClient, routes: Routes) -> None:
    program_id = await validated(routes.program, routes.user_id)
    body = {"available_minutes": 300, "message": "Cette semaine je n'ai que 5 heures."}
    r = await client.post(f"{API}/programs/{program_id}/replan", json=body)
    assert r.status_code == 202, r.text
    session_id = r.json()["session_id"]
    assert routes.launcher.started == [
        ("replan", {"program_id": program_id, "trigger": "message", **body})
    ]
    again = await client.post(f"{API}/programs/{program_id}/replan", json={})
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "replan_open"
    assert again.json()["error"]["details"] == {"session_id": session_id}
    await routes.launcher.end(routes.user_id, session_id)
    third = await client.post(f"{API}/programs/{program_id}/replan", json={})
    assert third.status_code == 202 and third.json()["session_id"] != session_id


async def test_start_replan_needs_validated_program(
    client: httpx.AsyncClient, routes: Routes
) -> None:
    program_id = await drafted(routes.program, routes.user_id)
    r = await client.post(f"{API}/programs/{program_id}/replan", json={})
    assert (r.status_code, r.json()["error"]["code"]) == (409, "program_not_validated")
    assert routes.launcher.started == []


async def test_replan_request_422_without_echo(client: httpx.AsyncClient, routes: Routes) -> None:
    program_id = await validated(routes.program, routes.user_id)
    secret = "Mon rendez-vous médical de jeudi " * 40  # 1 320 caractères
    for body in ({"available_minutes": 30}, {"message": secret}, {"available_minutes": 20000}):
        r = await client.post(f"{API}/programs/{program_id}/replan", json=body)
        assert r.status_code == 422 and "rendez-vous" not in r.text and "20000" not in r.text
    assert routes.launcher.started == []


async def test_versions_list_history_with_status(client: httpx.AsyncClient, routes: Routes) -> None:
    program_id = await validated(routes.program, routes.user_id)
    store = AgentReplanStore(routes.rt)
    ctx = await store.context(
        routes.user_id, program_id, trigger="message", review_entry_id=None,
        available_minutes=None, message=None,
    )  # fmt: skip
    for session in ("s-a", "s-b"):
        await store.preview(
            routes.user_id, session, program_id, ReplanDraft(summary="Je range."),
            refs=ctx.refs(), option=None, revision=0, reason="Message de January",
            week_cap_override=None,
        )  # fmt: skip
    await store.apply(routes.user_id, "s-b", program_id, 3)
    r = await client.get(f"{API}/programs/{program_id}/versions")
    assert r.status_code == 200, r.text
    listed = r.json()
    assert [(v["version"], v["kind"], v["status"]) for v in listed] == [
        (3, "replan", "accepted"),
        (2, "replan", "superseded"),
        (1, "build", "accepted"),
    ]
    latest = listed[0]
    assert latest["accepted_at"] and latest["session_id"] == "s-b" and latest["review"] is None
    assert latest["diff"]["moved"] and set(latest["diff"]["moved"][0]) == {
        "task",
        "before",
        "after",
    }
    assert latest["week_loads"] and all(w["after"] <= w["cap"] for w in latest["week_loads"])
    assert listed[2]["week_loads"] == [] and listed[2]["reason"]
    program = (await client.get(f"{API}/programs/{program_id}")).json()
    assert program["version"] == 3


async def test_replan_routes_isolate_users(client: httpx.AsyncClient, routes: Routes) -> None:
    theirs = await validated(routes.program, OTHER)
    r = await client.post(f"{API}/programs/{theirs}/replan", json={})
    assert (r.status_code, r.json()["error"]["code"]) == (404, "program_not_found")
    r = await client.get(f"{API}/programs/{theirs}/versions")
    assert (r.status_code, r.json()["error"]["code"]) == (404, "program_not_found")
    assert routes.launcher.started == []


async def test_generic_session_route_refuses_replan(
    client: httpx.AsyncClient, routes: Routes
) -> None:
    program_id = await validated(routes.program, routes.user_id)
    r = await client.post(
        f"{API}/sessions",
        json={"graph": "replan", "input": {"program_id": program_id, "trigger": "message"}},
    )
    assert (r.status_code, r.json()["error"]["code"]) == (409, "graph_has_route")


async def test_pending_of_closed_session_reads_superseded(
    client: httpx.AsyncClient, routes: Routes
) -> None:
    """I1 (relecture 5.9) : session annulée pendant qu'une proposition attend : lue
    `superseded` (D91, sans écriture) ; tant que la session est ouverte, `pending`."""
    program_id = await validated(routes.program, routes.user_id)
    r = await client.post(f"{API}/programs/{program_id}/replan", json={})
    session_id = r.json()["session_id"]
    store = AgentReplanStore(routes.rt)
    ctx = await store.context(
        routes.user_id, program_id, trigger="message", review_entry_id=None,
        available_minutes=None, message=None,
    )  # fmt: skip
    await store.preview(
        routes.user_id, session_id, program_id, ReplanDraft(summary="Je range."),
        refs=ctx.refs(), option=None, revision=0, reason="Message de January",
        week_cap_override=None,
    )  # fmt: skip

    async def status() -> str:
        listed = (await client.get(f"{API}/programs/{program_id}/versions")).json()
        return str(listed[0]["status"])

    assert await status() == "pending"
    await routes.launcher.end(routes.user_id, session_id, "cancelled")
    assert await status() == "superseded"
    stored = await versions(routes.app.state.session_factory, program_id)
    assert stored[-1]["status"] == "pending"  # lecture seule : rien n'est réécrit
