"""Une vérification réussie (`check`, code 0) : la séance est réussie, la compétence gagne une
preuve « ide » plafonnée à « en cours », le fil d'activité en parle. Un exercice ne valide rien."""

from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select

from app.agents.tools.plan_schema import SkillDraft
from app.core.skills import normalize_skill_name
from app.db.models.skills import Skill, UserSkill
from app.features.skills.service import SkillsService
from app.providers.sandbox.base import SandboxResult
from tests.features.ide.conftest import USER, UseSandbox
from tests.features.ide.mcp_support import acting_as_claude
from tests.features.ide.support import API, new_session, session_row, start_run

pytestmark = pytest.mark.usefixtures("me")

PASSED = "1 passed in 0.02s\n"


async def add_skill(app: FastAPI, name: str, level: str | None = None) -> str:
    """Une compétence de January (au niveau `level` si donné) ; rend son identifiant."""
    async with app.state.session_factory() as db:
        service = SkillsService(db, USER)
        ids = await service.upsert_catalog([SkillDraft(name=name, domain="python")], [])
        skill_id = ids[normalize_skill_name(name)]
        if level is not None:
            db.add(UserSkill(user_id=USER, skill_id=skill_id, level=level, evidence=[]))
        await db.commit()
        return skill_id


async def level_of(app: FastAPI, skill_id: str) -> tuple[str, list[dict[str, Any]]] | None:
    async with app.state.session_factory() as db:
        row = (
            await db.execute(select(UserSkill).where(UserSkill.skill_id == skill_id))
        ).scalar_one_or_none()
        return None if row is None else (row.level, list(row.evidence))


async def check(client: httpx.AsyncClient, session_id: str, kind: str = "check") -> dict[str, Any]:
    run = (await start_run(client, session_id, kind)).json()
    done: dict[str, Any] = (await client.get(f"{API}/runs/{run['id']}")).json()
    return done


async def test_check_pass_marks_session_passed_and_adds_proof_capped_en_cours(
    app: FastAPI, client: httpx.AsyncClient, use_sandbox: UseSandbox
) -> None:
    use_sandbox({"*": PASSED})
    skill_id = await add_skill(app, "Boucles")
    session = await new_session(client, title="Boucles")
    assert (await check(client, session["id"]))["status"] == "done"
    row = await session_row(app, session["id"])
    assert row.passed_at is not None
    got = (await client.get(f"{API}/sessions/{session['id']}")).json()
    assert got["passed"] is True and got["passed_at"] is not None
    summary = next(r for r in (await client.get(f"{API}/sessions")).json() if r["id"] == got["id"])
    assert summary["passed"] is True
    level, evidence = await level_of(app, skill_id) or ("", [])
    assert level == "in_progress"  # la compétence n'avait aucun niveau : créée à « en cours »
    assert [(e["kind"], e["ref_id"]) for e in evidence] == [("ide", session["id"])]
    assert evidence[0]["label"].startswith("Completed exercise") and evidence[0]["at"]


async def test_check_uses_the_exercise_topic_then_its_title(
    app: FastAPI, client: httpx.AsyncClient, use_sandbox: UseSandbox
) -> None:
    use_sandbox({"*": PASSED})
    by_title = await add_skill(app, "Fonctions")
    session = await new_session(client, title="Fonctions")
    await check(client, session["id"])
    assert (await level_of(app, by_title)) is not None


async def test_proof_never_reaches_valide(
    app: FastAPI, client: httpx.AsyncClient, use_sandbox: UseSandbox
) -> None:
    use_sandbox({"*": PASSED})
    declared = await add_skill(app, "Boucles", "declared")
    validated = await add_skill(app, "Fonctions", "validated")
    proven = await add_skill(app, "Classes", "proven")
    for title in ("Boucles", "Fonctions", "Classes"):
        await check(client, (await new_session(client, title=title))["id"])
    assert (await level_of(app, declared) or ("",))[0] == "in_progress"  # jamais plus haut
    for skill_id, level in ((validated, "validated"), (proven, "proven")):
        found = await level_of(app, skill_id)
        assert found is not None and found[0] == level  # le niveau ne baisse pas
        assert [e["kind"] for e in found[1]] == ["ide"]


async def test_passing_again_adds_no_second_proof_or_event(
    app: FastAPI, client: httpx.AsyncClient, use_sandbox: UseSandbox
) -> None:
    use_sandbox({"*": PASSED})
    skill_id = await add_skill(app, "Boucles")
    session = await new_session(client, title="Boucles")
    await check(client, session["id"])
    first = (await session_row(app, session["id"])).passed_at
    await check(client, session["id"])
    assert (await session_row(app, session["id"])).passed_at == first
    found = await level_of(app, skill_id)
    assert found is not None and len(found[1]) == 1


async def test_failing_or_plain_runs_do_not_pass(
    app: FastAPI, client: httpx.AsyncClient, use_sandbox: UseSandbox
) -> None:
    skill_id = await add_skill(app, "Boucles")
    session = await new_session(client, title="Boucles")
    use_sandbox({"*": SandboxResult("done", 1, 12, False)})  # pytest : des tests échouent
    await check(client, session["id"])
    use_sandbox({"*": SandboxResult("timeout", None, 10_000, False)})
    await check(client, session["id"])
    use_sandbox({"*": PASSED})
    await check(client, session["id"], kind="run")  # une exécution simple ne prouve rien
    assert (await session_row(app, session["id"])).passed_at is None
    assert await level_of(app, skill_id) is None


async def test_pass_without_matching_skill_creates_nothing(
    app: FastAPI, client: httpx.AsyncClient, use_sandbox: UseSandbox
) -> None:
    use_sandbox({"*": PASSED})
    session = await new_session(client, title="Sujet sans compétence")
    await check(client, session["id"])
    assert (await session_row(app, session["id"])).passed_at is not None
    async with app.state.session_factory() as db:
        assert (await db.execute(select(Skill))).first() is None


async def test_activity_event_on_pass(
    app: FastAPI, client: httpx.AsyncClient, use_sandbox: UseSandbox
) -> None:
    use_sandbox({"*": PASSED})
    session = await new_session(client, title="Boucles")
    assert (await client.get("/api/v1/activity")).json()["items"] == []
    await check(client, session["id"])
    [item] = (await client.get("/api/v1/activity")).json()["items"]
    assert item["id"] == f"ide:{session['id']}:passed" and item["kind"] == "project"
    assert item["title"] == "Coding exercise passed: Boucles"
    assert item["link"] == f"/code/{session['id']}"
    await check(client, session["id"])  # un second passage n'ajoute rien
    assert len((await client.get("/api/v1/activity")).json()["items"]) == 1


async def test_a_check_run_by_claude_never_passes_the_session_nor_adds_a_proof(
    app: FastAPI, client: httpx.AsyncClient, use_sandbox: UseSandbox
) -> None:
    """Seule une vérification de January valide l'exercice : Claude ne le valide pas à sa place."""
    use_sandbox({"*": PASSED})
    skill_id = await add_skill(app, "Boucles")
    session = await new_session(client, title="Boucles")
    with acting_as_claude():
        run = await check(client, session["id"])
    assert (run["status"], run["exit_code"]) == ("done", 0)
    assert (await session_row(app, session["id"])).passed_at is None
    assert (await client.get(f"{API}/sessions/{session['id']}")).json()["passed"] is False
    assert await level_of(app, skill_id) is None
    # la vérification de January, elle, compte
    await check(client, session["id"])
    assert (await session_row(app, session["id"])).passed_at is not None
    assert (await level_of(app, skill_id) or ("",))[0] == "in_progress"
