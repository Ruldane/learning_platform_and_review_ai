"""Relevés fictifs de salaire pour l'API et la recette de négociation."""

import json
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI

from app.core.skills import normalize_skill_name
from app.db.models.daily import RadarRun
from tests.agents.graphs.interview_support import debrief_json
from tests.features.applications.interview_support import add_profile

ROLE = "Ingénieure IA"
ZONE = "Lyon"
BODY = {"mode": "salary", "duration_min": 15, "role": "ingenieure ia", "radar_zone": "lyon"}
ANSWER = "Je souhaite renégocier la base. Le support du service est une responsabilité utile."
SCRIPT = [
    json.dumps({"follow_up": "Je propose 99 000 €.", "note": 4, "salary_move": True}),
    debrief_json(improved_answer="Je demande 99 000 € comme si c'était le budget."),
]


async def add_salary_run(
    app: FastAPI,
    user_id: str,
    *,
    role: str = ROLE,
    zone: str = ZONE,
    day: int,
    salaries: list[str | None],
) -> str:
    at = datetime(2026, 11, day, 10, tzinfo=UTC)
    entries: list[dict[str, Any]] = [
        {"read": "ok", "skills": [], "salary": salary} for salary in salaries
    ]
    async with app.state.session_factory() as db:
        row = RadarRun(
            user_id=user_id,
            role=role,
            zone=zone,
            role_norm=normalize_skill_name(role),
            zone_norm=normalize_skill_name(zone),
            trigger="manual",
            status="done",
            created_at=at,
            finished_at=at,
            analyzed=len(entries),
            read_count=len(entries),
            postings=entries,
        )
        db.add(row)
        await db.commit()
        return str(row.id)


async def seed_negotiation(app: FastAPI) -> str:
    await add_profile(app)
    me: str = app.state.local_user_id
    sample = await add_salary_run(
        app, me, day=11, salaries=["50 à 65 k€ bruts par an", "70 000 € brut annuel", "900 €/jour"]
    )
    await add_salary_run(app, me, day=13, zone="Paris", salaries=["100 k€ brut annuel"])
    await add_salary_run(app, me, day=14, role="Comptable", salaries=["80 k€ brut annuel"])
    await add_salary_run(app, "autre-compte", day=15, salaries=["110 k€ brut annuel"])
    return sample
