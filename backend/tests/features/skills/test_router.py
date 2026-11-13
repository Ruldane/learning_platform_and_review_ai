"""Routes de la carte de compétences (D107) : lecture sans cache, bornes de `weeks` (422 sans
recopier la saisie), isolation entre deux utilisateurs."""

import httpx
from fastapi import FastAPI

from app.core.skills import evidence
from app.features.skills.router import clock
from app.features.skills.service import SkillsService
from tests.features.skills.support import (
    API,
    NOW,
    WEEK,
    Factory,
    add_edge,
    add_goal,
    add_program,
    add_skill,
    add_snapshot,
)

OTHER = "autre"


def _me(app: FastAPI) -> str:
    return str(app.state.local_user_id)


async def test_graph_reflects_level_change_immediately(
    app: FastAPI, client: httpx.AsyncClient, db_session_factory: Factory
) -> None:
    me = _me(app)
    skill_id = await add_skill(db_session_factory, me, "Pandas", "Données", "declare")
    first = await client.get(f"{API}/skills/graph")
    assert first.status_code == 200, first.text
    assert first.headers["cache-control"] == "no-store"
    assert [(n["id"], n["level"], n["evidence_count"]) for n in first.json()["nodes"]] == [
        (skill_id, "declare", 0)
    ]
    async with db_session_factory() as db:
        proof = evidence("quiz", "q1", "Quiz « Bases » : 85 %", NOW)
        await SkillsService(db, me).raise_levels(["pandas"], "valide", proof)
        await db.commit()
    body = (await client.get(f"{API}/skills/graph")).json()
    assert [(n["level"], n["evidence_count"]) for n in body["nodes"]] == [("valide", 1)]
    assert body["domains"] == [{"domain": "Données", "score": 75}]
    detail = (await client.get(f"{API}/skills/{skill_id}")).json()
    assert detail["level"] == "valide"
    assert detail["evidence"] == [
        {
            "kind": "quiz",
            "label": "Quiz « Bases » : 85 %",
            "at": "2026-11-17T10:00:00Z",
            "url": "/etudier/quiz/q1",
        }
    ]
    assert detail["next_action"] == {
        "kind": "project",
        "label": "Projet preuve (bientôt)",
        "url": None,
    }


async def test_history_weeks_bounds_422_without_echo(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    for value in ("0", "777", "secret-xyz"):
        r = await client.get(f"{API}/skills/history", params={"weeks": value})
        assert r.status_code == 422, r.text
        assert r.json()["error"]["code"] == "validation_error"
        assert value not in r.text
    for value in ("1", "52"):
        assert (
            await client.get(f"{API}/skills/history", params={"weeks": value})
        ).status_code == 200
    r = await client.get(f"{API}/skills/compare", params={"target": "secret-offre"})
    assert r.status_code == 422 and "secret-offre" not in r.text


async def test_history_route_uses_clock(
    app: FastAPI, client: httpx.AsyncClient, db_session_factory: Factory
) -> None:
    app.dependency_overrides[clock] = lambda: NOW
    me = _me(app)
    skill_id = await add_skill(db_session_factory, me, "Pandas", None, "en_cours")
    await add_snapshot(db_session_factory, me, WEEK.replace(day=9), {skill_id: "declare"})
    r = await client.get(f"{API}/skills/history")
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    assert r.json() == {
        "points": [
            {
                "week_start": "2026-11-09",
                "counts": {"declare": 1, "en_cours": 0, "valide": 0, "prouve": 0},
                "score": 25,
            },
            {
                "week_start": "2026-11-16",
                "counts": {"declare": 0, "en_cours": 1, "valide": 0, "prouve": 0},
                "score": 50,
            },
        ]
    }


async def test_skills_routes_isolate_users(
    app: FastAPI, client: httpx.AsyncClient, db_session_factory: Factory
) -> None:
    app.dependency_overrides[clock] = lambda: NOW
    a = await add_skill(db_session_factory, OTHER, "Pandas", "Données", "prouve", ["Programme"])
    b = await add_skill(db_session_factory, OTHER, "NumPy", "Données", "valide")
    await add_edge(db_session_factory, OTHER, b, a)
    await add_snapshot(db_session_factory, OTHER, WEEK.replace(day=9), {a: "valide"})
    goal = await add_goal(db_session_factory, OTHER, target_role="Data engineer")
    await add_program(db_session_factory, OTHER, goal, [("Bases", ["pandas", "numpy"])])

    graph = (await client.get(f"{API}/skills/graph")).json()
    assert graph == {"nodes": [], "edges": [], "domains": []}
    detail = await client.get(f"{API}/skills/{a}")
    assert (detail.status_code, detail.json()["error"]["code"]) == (404, "skill_not_found")
    foreign = await client.get(f"{API}/skills/compare", params={"goal_id": goal})
    assert (foreign.status_code, foreign.json()["error"]["code"]) == (404, "goal_not_found")
    default = await client.get(f"{API}/skills/compare")
    assert (default.status_code, default.json()["error"]["code"]) == (404, "no_compare_target")
    history = (await client.get(f"{API}/skills/history")).json()
    assert history["points"] == [
        {
            "week_start": "2026-11-16",
            "counts": {"declare": 0, "en_cours": 0, "valide": 0, "prouve": 0},
            "score": 0,
        }
    ]
    # Ma propre compétence, au même nom, reste à moi seule.
    mine = await add_skill(db_session_factory, _me(app), "Pandas", "Données", "declare")
    nodes = (await client.get(f"{API}/skills/graph")).json()["nodes"]
    assert [(n["id"], n["level"]) for n in nodes] == [(mine, "declare")]
