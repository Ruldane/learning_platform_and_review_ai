"""Programme complet écrit en direct (`POST /programs/direct`) : semaines, modules et tâches en un
appel, rangés par les règles du Stratège, sans agent ni appel au modèle ; le programme entre « à
valider » et se valide comme celui de l'agent."""

from datetime import date
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select

from app.db.models.learning import Goal
from app.db.models.program import PlanVersion
from app.db.models.skills import UserSkill
from app.features.program.service.planning import next_monday
from tests.features.program.support import tasks_of, view
from tests.sessions_support import act_as
from tests.support.direct import API, OTHER, assert_no_agent
from tests.support.lesson_verification import submission_text, wait_session

START = next_monday(date.today())  # un début accepté : un lundi, aujourd'hui ou plus tard
SECRET = "SECRET-DU-PROGRAMME"
GOAL = {"text": "Les bases du ML pour l'ingénierie IA", "weekly_hours": 7}


def week(theme: str, minutes: list[int], skill: str) -> dict[str, Any]:
    """Une semaine d'un module : des lectures, puis la pratique et le quiz."""
    tasks = [
        {
            "title": f"Lire le chapitre {i}",
            "type": "lire",
            "minutes": m,
            "done_criterion": "Notes prises",
        }
        for i, m in enumerate(minutes, start=1)
    ]
    tasks += [
        {
            "title": f"Pratiquer {theme}",
            "type": "pratiquer",
            "minutes": 45,
            "done_criterion": "Un résultat montrable",
        },
        {"title": "Faire le quiz", "type": "quiz", "minutes": 20, "done_criterion": "Quiz relu"},
    ]
    return {
        "theme": theme,
        "objective": "Savoir faire",
        "deliverable": "Un dépôt",
        "modules": [{"title": f"Module {theme}", "skills": [skill], "tasks": tasks}],
    }


def program_body(goal_id: str, **over: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "goal_id": goal_id,
        "title": "Les bases du ML",
        "start_date": START.isoformat(),
        "weeks": [
            week("Régression", [60, 60, 60, 60], "régression linéaire"),
            week("Arbres", [60, 60, 40, 40], "arbres de décision"),
        ],
    }
    return {**body, **over}


async def new_goal(client: httpx.AsyncClient) -> str:
    r = await client.post(f"{API}/goals/direct", json=GOAL)
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


async def versions(app: FastAPI) -> list[PlanVersion]:
    async with app.state.session_factory() as db:
        return list((await db.execute(select(PlanVersion))).scalars().all())


async def test_direct_program_is_written_as_a_draft_to_validate(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    goal_id = await new_goal(client)

    r = await client.post(f"{API}/programs/direct", json=program_body(goal_id))

    assert r.status_code == 201, r.text
    program = r.json()
    assert (program["goal_id"], program["title"], program["status"]) == (
        goal_id,
        "Les bases du ML",
        "draft",
    )
    assert program["start_date"] == START.isoformat() and program["session_id"] is None
    assert [w["theme"] for w in program["weeks"]] == ["Régression", "Arbres"]
    assert program["weeks"][0]["start_date"] == START.isoformat()
    module = program["weeks"][0]["modules"][0]
    assert (module["title"], module["skills"]) == ("Module Régression", ["régression linéaire"])
    assert len(tasks_of(program)) == 12
    assert program["cap_minutes"] == 357  # 85 % des 7 h par semaine de l'objectif
    assert (await view(client, program["id"]))["status"] == "draft"
    goal = (await client.get(f"{API}/goals/{goal_id}")).json()
    assert goal["program_id"] == program["id"] and goal["status"] == "chosen"
    [version] = await versions(app)
    assert (version.status, version.kind, version.session_id) == ("pending", "build", None)
    assert version.program_id == program["id"] and version.version == program["version"] == 1
    await assert_no_agent(app)


async def test_direct_program_starts_next_monday_by_default(client: httpx.AsyncClient) -> None:
    goal_id = await new_goal(client)
    body = program_body(goal_id)
    del body["start_date"]

    r = await client.post(f"{API}/programs/direct", json=body)

    assert r.status_code == 201, r.text
    start = date.fromisoformat(r.json()["start_date"])
    assert start.weekday() == 0 and start >= date.today()


async def test_direct_program_is_scheduled_within_the_weekly_cap(
    client: httpx.AsyncClient,
) -> None:
    """Les tâches reçoivent un jour, rangées comme pour le Stratège : jamais plus de 85 %."""
    goal_id = await new_goal(client)

    r = await client.post(f"{API}/programs/direct", json=program_body(goal_id))

    assert r.status_code == 201, r.text
    days = [t["planned_date"] for t in tasks_of(r.json())]
    assert all(START.isoformat() <= day for day in days)
    assert all(w["load_minutes"] <= r.json()["cap_minutes"] for w in r.json()["weeks"])
    assert [w["load_minutes"] for w in r.json()["weeks"]] == [305, 265]


async def test_direct_program_catalog_and_edges_are_kept_for_the_skill_graph(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    goal_id = await new_goal(client)
    skills = [
        {"name": "régression linéaire", "domain": "Statistiques"},
        {"name": "arbres de décision", "domain": "Apprentissage"},
    ]
    edges = [{"before": "régression linéaire", "after": "arbres de décision"}]

    r = await client.post(
        f"{API}/programs/direct", json=program_body(goal_id, skills=skills, edges=edges)
    )

    assert r.status_code == 201, r.text
    [version] = await versions(app)
    catalog = version.snapshot["catalog"]
    assert [s["name"] for s in catalog["skills"]] == [s["name"] for s in skills]
    assert len(catalog["edges"]) == 1


async def test_direct_program_without_catalog_gets_one_from_its_modules(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    goal_id = await new_goal(client)

    assert (
        await client.post(f"{API}/programs/direct", json=program_body(goal_id))
    ).status_code == 201

    [version] = await versions(app)
    names = [s["name"] for s in version.snapshot["catalog"]["skills"]]
    assert names == ["régression linéaire", "arbres de décision"]


async def test_direct_program_validates_like_an_agent_program(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    goal_id = await new_goal(client)
    created = (await client.post(f"{API}/programs/direct", json=program_body(goal_id))).json()

    validated = await client.post(f"{API}/programs/{created['id']}/validate")

    assert validated.status_code == 202, validated.text
    assert (validated.json()["status"], validated.json()["session_id"]) == ("validated", None)
    assert (await view(client, created["id"]))["status"] == "validated"
    async with app.state.session_factory() as db:
        goal = (await db.execute(select(Goal).where(Goal.id == goal_id))).scalar_one()
        levels = (await db.execute(select(UserSkill.level))).scalars().all()
    assert goal.status == "planned"
    assert [v.status for v in await versions(app)] == ["accepted"]  # la version écrite, acceptée
    assert list(levels) == ["en_cours", "en_cours"]  # les compétences des deux modules


@pytest.mark.usefixtures("accept_lesson")
async def test_direct_program_can_be_filled_with_the_existing_tools(
    client: httpx.AsyncClient,
) -> None:
    """Les routes de 10.W suffisent : leçon d'un module, tâche retouchée."""
    goal_id = await new_goal(client)
    program = (await client.post(f"{API}/programs/direct", json=program_body(goal_id))).json()
    module = program["weeks"][0]["modules"][0]
    text = submission_text(module["title"])

    lesson = await client.post(f"{API}/modules/{module['id']}/lesson", json={"markdown": text})
    assert lesson.status_code == 202, lesson.text
    assert (await wait_session(client, lesson.json()["verification_session_id"]))[
        "status"
    ] == "completed"
    patched = await client.patch(
        f"{API}/tasks/{module['tasks'][0]['id']}", json={"title": "Lire le chapitre un"}
    )

    assert patched.status_code == 200, patched.text
    after = await view(client, program["id"])
    assert after["weeks"][0]["modules"][0]["lesson_status"] == "ready"
    assert "Lire le chapitre un" in [t["title"] for t in tasks_of(after)]


async def test_direct_program_unknown_goal_and_second_program_are_refused(
    client: httpx.AsyncClient,
) -> None:
    unknown = await client.post(f"{API}/programs/direct", json=program_body("inconnu"))
    assert (unknown.status_code, unknown.json()["error"]["code"]) == (404, "goal_not_found")

    goal_id = await new_goal(client)
    first = await client.post(f"{API}/programs/direct", json=program_body(goal_id))
    again = await client.post(f"{API}/programs/direct", json=program_body(goal_id))

    assert first.status_code == 201
    assert (again.status_code, again.json()["error"]["code"]) == (409, "program_exists")
    assert len((await client.get(f"{API}/programs")).json()) == 1


async def test_direct_program_of_another_user_is_404_and_writes_nothing(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    goal_id = await new_goal(client)
    act_as(app, OTHER)

    r = await client.post(f"{API}/programs/direct", json=program_body(goal_id))

    assert (r.status_code, r.json()["error"]["code"]) == (404, "goal_not_found")
    assert (await client.get(f"{API}/programs")).json() == []
    await assert_no_agent(app)


async def test_direct_program_breaking_the_rules_is_422_with_the_problems(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    heavy = week("Trop", [60] * 8, "tout")  # 545 minutes : au-delà du plafond de 357
    no_quiz = week("Arbres", [60, 60, 40, 40], "arbres")
    no_quiz["modules"][0]["tasks"].pop()  # et un quiz manquant
    weeks = [heavy, no_quiz]

    r = await client.post(
        f"{API}/programs/direct", json=program_body(await new_goal(client), weeks=weeks)
    )

    assert r.status_code == 422, r.text
    error = r.json()["error"]
    assert error["code"] == "plan_invalid"
    assert error["details"]["problems"] == [
        "Semaine 1 : 545 min prévues, 357 au plus.",
        "Semaine 2 : aucun quiz.",
    ]
    assert (await client.get(f"{API}/programs")).json() == []
    await assert_no_agent(app)


async def test_direct_program_keeps_the_book_fields(client: httpx.AsyncClient) -> None:
    """Écrit en direct, un programme garde l'étape et la raison de chaque semaine, les pages
    officielles et l'encadré « code ancien » de chaque chapitre, et l'ordre de ses notions."""
    body = program_body(await new_goal(client))
    first, second = body["weeks"]
    first |= {"stage": "fondations", "rationale": "Le socle de tout le reste."}
    second |= {"stage": "pratique", "rationale": "On applique la régression aux arbres."}
    first["modules"][0] |= {
        "official_urls": ["https://scikit-learn.org/stable/modules/linear_model.html"],
        "legacy": ["sklearn.cross_validation"],
        "introduces": [{"name": "régression", "definition": "Prédire une valeur continue."}],
    }
    second["modules"][0] |= {"requires": ["régression"]}
    r = await client.post(f"{API}/programs/direct", json=body)
    assert r.status_code == 201, r.text
    weeks = r.json()["weeks"]
    assert [(w["stage"], w["rationale"]) for w in weeks] == [
        ("fondations", "Le socle de tout le reste."),
        ("pratique", "On applique la régression aux arbres."),
    ]
    module = weeks[0]["modules"][0]
    assert module["official_urls"] == ["https://scikit-learn.org/stable/modules/linear_model.html"]
    assert module["legacy"] == ["sklearn.cross_validation"]


async def test_direct_program_refuses_a_notion_used_before_it_is_introduced(
    client: httpx.AsyncClient,
) -> None:
    body = program_body(await new_goal(client))
    body["weeks"][0]["modules"][0]["requires"] = ["régression"]
    r = await client.post(f"{API}/programs/direct", json=body)
    assert r.status_code == 422, r.text
    assert "régression" not in r.text  # une 422 ne renvoie jamais l'entrée reçue
