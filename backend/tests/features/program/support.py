"""Matériel des tests de la feature `program` : un plan de deux semaines dont on connaît la
charge (rangé par les vraies règles de 4.2), un objectif et sa proposition en base, et des
lectures de la vue de l'API."""

from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import uuid4

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.tools.plan_schema import EdgeDraft, PlanDraft, SkillDraft
from app.db.models.learning import Goal, Proposal
from tests.support.program import module, task, week

Factory = async_sessionmaker[AsyncSession]
MONDAY = date(2026, 11, 16)  # semaine 1 : 16 au 22/11 ; semaine 2 : 23 au 29/11
TUESDAY_W1 = "2026-11-17"
API = "/api/v1"
CAP = 714  # 85 % de 840 (disponibilités par défaut)
WEEK1_LOAD = 665  # cinq lectures de 120, pratique 45, quiz 20
WEEK2_LOAD = 205  # lectures de 40, 40 et 60, pratique 45, quiz 20


def sample_plan(skills: tuple[str, str] = ("pandas", "numpy")) -> PlanDraft:
    first, second = skills
    w1 = week(
        "Bases",
        [
            module(
                "Module Bases",
                [task(f"Lire le chapitre {i}", minutes=120) for i in range(1, 6)]
                + [
                    task("Pratiquer les bases", "pratiquer", 45),
                    task("Faire le quiz 1", "quiz", 20),
                ],
                skills=[first],
            )
        ],
    )
    w2 = week(
        "Projet",
        [
            module(
                "Module Projet",
                [
                    task("Lire l'article A", minutes=40),
                    task("Lire l'article B", minutes=40),
                    task("Lire l'article C", minutes=60),
                    task("Pratiquer le projet", "pratiquer", 45),
                    task("Faire le quiz 2", "quiz", 20),
                ],
                skills=[second],
            )
        ],
    )
    return PlanDraft(
        title="Parcours données",
        weeks=[w1, w2],
        skills=[SkillDraft(name=first, domain="Données"), SkillDraft(name=second, domain="Calcul")],
        edges=[EdgeDraft(before=second, after=first)],
    )


@dataclass(frozen=True)
class GoalRows:
    goal_id: str
    proposal_id: str


async def add_goal(
    factory: Factory, user_id: str, *, weekly_minutes: int | None = None
) -> GoalRows:
    async with factory() as db:
        goal = Goal(
            user_id=user_id,
            text="Devenir data engineer",
            framing={},
            status="chosen",
            weekly_minutes=weekly_minutes,
        )
        db.add(goal)
        await db.flush()
        proposal = Proposal(
            user_id=user_id,
            goal_id=goal.id,
            session_id=f"council-{uuid4().hex}",
            batch=1,
            rank=1,
            name="Parcours données",
            promise="Une promesse assez longue pour le schéma.",
            duration_weeks=2,
            weekly_hours=10,
            skills=["pandas"],
            final_project="Un projet final complet et démontrable.",
            tradeoffs=["Moins de théorie"],
            chosen=True,
        )
        db.add(proposal)
        await db.commit()
    return GoalRows(goal.id, proposal.id)


async def view(client: httpx.AsyncClient, program_id: str) -> dict[str, Any]:
    r = await client.get(f"{API}/programs/{program_id}")
    assert r.status_code == 200, r.text
    body: dict[str, Any] = r.json()
    return body


def tasks_of(program: dict[str, Any]) -> list[dict[str, Any]]:
    return [t for w in program["weeks"] for m in w["modules"] for t in m["tasks"]]


def task_id(program: dict[str, Any], title: str) -> str:
    return next(str(t["id"]) for t in tasks_of(program) if t["title"] == title)


def week_load(program: dict[str, Any], rank: int) -> int:
    return int(next(w["load_minutes"] for w in program["weeks"] if w["rank"] == rank))
