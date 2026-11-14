"""« Ajouter au planning » (D123) : `POST /postings/{id}/gap/plan` lance une replanification au
déclencheur `gap` du programme validé ; les compétences doivent être des lignes `to_add` (422 sans
valeur), un programme validé est requis (409 `no_program`), une replanification ouverte bloque
(409 `replan_open`). À l'acceptation, le module « Compétences des offres » est créé une fois, en
fin de programme, puis réutilisé, et la ligne de l'écart passe `in_program`."""

from dataclasses import dataclass
from datetime import UTC, datetime

import httpx
import pytest
from fastapi import FastAPI

from app.agents.tools.replan_port import GAP_MODULE_TITLE, ReplanDraft, ReplanTaskDraft
from app.features.program.service.programs import load
from app.features.program.service.runtime import ProgramRuntime
from app.features.replan.service.store import AgentReplanStore
from tests.features.lessons.conftest import RecordingLauncher
from tests.features.postings.conftest import API, analyzed_posting
from tests.features.replan.conftest import drafted, validated

NOW = datetime(2026, 11, 18, 9, 0, tzinfo=UTC)  # mercredi de la semaine 1 de `sample_plan`


@dataclass
class Plan:
    app: FastAPI
    user_id: str
    launcher: RecordingLauncher

    @property
    def program(self) -> ProgramRuntime:
        return ProgramRuntime(self.app.state.session_factory, self.app.state.memory)

    @property
    def store(self) -> AgentReplanStore:
        return AgentReplanStore(self.app.state.replan)


@pytest.fixture
def plan(client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher) -> Plan:
    launcher = RecordingLauncher(app.state.session_factory)
    app.state.replan.launcher = launcher
    app.state.replan.now = lambda: NOW
    return Plan(app, app.state.local_user_id, launcher)


async def _posting(client: httpx.AsyncClient, plan: Plan) -> str:
    """Une offre analysée, écart rangé : « LangGraph » et « Évaluation de RAG » sans
    rattachement, donc `to_add`."""
    return await analyzed_posting(client, plan.app)


async def _row(client: httpx.AsyncClient, posting_id: str, skill: str) -> dict[str, object]:
    rows = (await client.get(f"{API}/postings/{posting_id}/gap")).json()["rows"]
    found: dict[str, object] = next(row for row in rows if row["skill"] == skill)
    return found


async def _apply(plan: Plan, session_id: str, program_id: str, skill: str, title: str) -> None:
    """Ce que fait le parcours `replan` accepté : contexte, proposition, acceptation."""
    ctx = await plan.store.context(
        plan.user_id, program_id, trigger="gap", review_entry_id=None, available_minutes=None,
        message=None, skills=[skill],
    )  # fmt: skip
    assert ctx.modules[0].ref == "m0" and ctx.modules[0].title == GAP_MODULE_TITLE
    task = ReplanTaskDraft(
        module="m0", title=title, type="pratiquer", minutes=45, done_criterion="Montré"
    )
    draft = ReplanDraft(summary="J'ajoute.", add=[task], drop=["t1"])
    saved = await plan.store.preview(
        plan.user_id, session_id, program_id, draft, refs=ctx.refs(), option=None, revision=0,
        reason="Compétences des offres", week_cap_override=None,
    )  # fmt: skip
    assert (saved.added, saved.removed) == (1, 0)  # le retrait est ignoré (ajouts seuls)
    applied = await plan.store.apply(plan.user_id, session_id, program_id, saved.version)
    assert not applied.stale
    await plan.launcher.end(plan.user_id, session_id)


async def test_plan_gap_starts_a_gap_replan(client: httpx.AsyncClient, plan: Plan) -> None:
    program_id = await validated(plan.program, plan.user_id)
    posting_id = await _posting(client, plan)
    body = {"skills": ["langgraph", "LangGraph", "Évaluation de RAG"]}
    r = await client.post(f"{API}/postings/{posting_id}/gap/plan", json=body)
    assert r.status_code == 202, r.text
    payload = {"program_id": program_id, "trigger": "gap"}
    assert plan.launcher.started == [
        ("replan", payload | {"skills": ["LangGraph", "Évaluation de RAG"]})
    ]
    again = await client.post(f"{API}/postings/{posting_id}/gap/plan", json=body)
    assert (again.status_code, again.json()["error"]["code"]) == (409, "replan_open")
    assert again.json()["error"]["details"] == {"session_id": r.json()["session_id"]}


async def test_plan_gap_rejects_skill_not_to_add(client: httpx.AsyncClient, plan: Plan) -> None:
    await validated(plan.program, plan.user_id)
    posting_id = await _posting(client, plan)
    secret = "Compétence secrète de January"
    r = await client.post(
        f"{API}/postings/{posting_id}/gap/plan", json={"skills": ["LangGraph", secret]}
    )
    assert r.status_code == 422 and r.json()["error"]["code"] == "gap_skill_unknown"
    assert r.json()["error"]["details"] == {"fields": ["skills.1"]}
    assert secret not in r.text and plan.launcher.started == []
    for body in ({"skills": []}, {"skills": [secret] * 11}, {"skills": ["x" * 121]}):
        r = await client.post(f"{API}/postings/{posting_id}/gap/plan", json=body)
        assert r.status_code == 422 and "secrète" not in r.text and "xxxx" not in r.text


async def test_plan_gap_without_program_is_409(client: httpx.AsyncClient, plan: Plan) -> None:
    await drafted(plan.program, plan.user_id)  # un brouillon ne compte pas
    posting_id = await _posting(client, plan)
    r = await client.post(f"{API}/postings/{posting_id}/gap/plan", json={"skills": ["LangGraph"]})
    assert r.status_code == 409 and r.json()["error"] == {
        "code": "no_program",
        "message": "Aucun programme validé : crée d'abord ton programme.",
        "details": None,
    }
    other = await client.post(f"{API}/postings/inconnue/gap/plan", json={"skills": ["LangGraph"]})
    assert other.status_code == 404 and other.json()["error"]["code"] == "posting_not_found"


async def test_gap_module_created_once(client: httpx.AsyncClient, plan: Plan) -> None:
    program_id = await validated(plan.program, plan.user_id)
    posting_id = await _posting(client, plan)
    for skill, title in (
        ("LangGraph", "Pratiquer LangGraph sur un agent"),
        ("Évaluation de RAG", "Pratiquer l'évaluation de RAG"),
    ):
        r = await client.post(f"{API}/postings/{posting_id}/gap/plan", json={"skills": [skill]})
        assert r.status_code == 202, r.text
        await _apply(plan, r.json()["session_id"], program_id, skill, title)
    async with plan.app.state.session_factory() as db:
        loaded = await load(db, plan.user_id, program_id)
    modules = [m for m in loaded.modules if m.title == GAP_MODULE_TITLE]
    assert len(modules) == 1
    module = modules[0]
    assert module.skills == ["LangGraph", "Évaluation de RAG"]
    assert module.week_id == loaded.weeks[-1].id  # en fin de programme
    assert module.rank == 1  # après le module de la dernière semaine
    titles = [t.title for t in loaded.tasks_of_module(module.id)]
    assert titles == ["Pratiquer LangGraph sur un agent", "Pratiquer l'évaluation de RAG"]
    assert len(loaded.tasks) == 14  # 12 tâches du plan + 2 ajouts, aucun retrait


async def test_row_becomes_in_program_after_apply(client: httpx.AsyncClient, plan: Plan) -> None:
    program_id = await validated(plan.program, plan.user_id)
    posting_id = await _posting(client, plan)
    assert (await _row(client, posting_id, "LangGraph"))["action"] == "to_add"
    r = await client.post(f"{API}/postings/{posting_id}/gap/plan", json={"skills": ["LangGraph"]})
    await _apply(plan, r.json()["session_id"], program_id, "LangGraph", "Pratiquer LangGraph")
    row = await _row(client, posting_id, "LangGraph")
    assert (row["action"], row["week"]) == ("in_program", 2)
    assert (await _row(client, posting_id, "Évaluation de RAG"))["action"] == "to_add"
    # Déjà au programme : ce n'est plus une ligne à ajouter.
    again = await client.post(
        f"{API}/postings/{posting_id}/gap/plan", json={"skills": ["LangGraph"]}
    )
    assert (again.status_code, again.json()["error"]["details"]) == (422, {"fields": ["skills.0"]})


async def test_refused_proposal_creates_no_module(client: httpx.AsyncClient, plan: Plan) -> None:
    program_id = await validated(plan.program, plan.user_id)
    posting_id = await _posting(client, plan)
    r = await client.post(f"{API}/postings/{posting_id}/gap/plan", json={"skills": ["LangGraph"]})
    session_id = r.json()["session_id"]
    ctx = await plan.store.context(
        plan.user_id, program_id, trigger="gap", review_entry_id=None, available_minutes=None,
        message=None, skills=["LangGraph"],
    )  # fmt: skip
    task = ReplanTaskDraft(
        module="m0", title="Pratiquer LangGraph", type="pratiquer", minutes=45,
        done_criterion="Montré",
    )  # fmt: skip
    saved = await plan.store.preview(
        plan.user_id, session_id, program_id, ReplanDraft(summary="J'ajoute.", add=[task]),
        refs=ctx.refs(), option=None, revision=0, reason="Compétences des offres",
        week_cap_override=None,
    )  # fmt: skip
    assert saved.added == 1 and not saved.empty
    await plan.store.refuse(plan.user_id, session_id, program_id, saved.version)
    async with plan.app.state.session_factory() as db:
        loaded = await load(db, plan.user_id, program_id)
    assert all(m.title != GAP_MODULE_TITLE for m in loaded.modules) and len(loaded.tasks) == 12
    assert (await _row(client, posting_id, "LangGraph"))["action"] == "to_add"
