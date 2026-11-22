"""Données synthétiques lues par la vraie route de projection."""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.skills import normalize_skill_name
from app.db.models.daily import RadarRun
from app.db.models.learning import Goal
from app.db.models.lessons import Lesson
from app.db.models.program import Module, Program, Task, Week
from app.db.models.skills import Skill, UserSkill
from app.db.models.study import StudySession
from app.features.future_self import service

API = "/api/v1/future-self"
TODAY = date(2026, 11, 16)
ROLE = "Ingénieur IA"
ZONE = "France"


def freeze_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(service, "local_today", lambda _: TODAY)


def _run(
    user_id: str, role: str, day: int, offers: list[list[str]], *, zone: str = ZONE
) -> RadarRun:
    at = datetime(2026, 11, day, tzinfo=UTC)
    postings: list[dict[str, Any]] = [
        {
            "read": "ok",
            "key": f"jobs.example.org/fictive-{index}",
            "skills": [{"name": name, "required": True} for name in names],
            "score": 100,  # le calcul doit relire les niveaux, pas le score historique
        }
        for index, names in enumerate(offers)
    ]
    return RadarRun(
        user_id=user_id,
        role=role,
        zone=zone,
        role_norm=normalize_skill_name(role),
        zone_norm=normalize_skill_name(zone),
        status="done",
        trigger="manual",
        created_at=at,
        finished_at=at,
        read_count=len(postings),
        analyzed=len(postings),
        postings=postings,
    )


async def _program(db: AsyncSession, user_id: str) -> tuple[Program, Module, Lesson]:
    goal = Goal(user_id=user_id, text="Programme synthétique", target_role=ROLE, status="planned")
    db.add(goal)
    await db.flush()
    program = Program(
        user_id=user_id,
        title="Parcours IA",
        goal_id=goal.id,
        status="validated",
        start_date=TODAY,
        weekly_minutes=180,
        cap_minutes=153,
    )
    db.add(program)
    await db.flush()
    week = Week(
        user_id=user_id,
        program_id=program.id,
        rank=1,
        theme="Recherche",
        objective="Appliquer",
        deliverable="Projet",
        start_date=TODAY,
    )
    db.add(week)
    await db.flush()
    module, lesson = await _material(db, user_id, program.id, week.id)
    return program, module, lesson


async def _material(
    db: AsyncSession, user_id: str, program_id: str, week_id: str
) -> tuple[Module, Lesson]:
    module = Module(
        user_id=user_id,
        program_id=program_id,
        week_id=week_id,
        rank=0,
        title="Recherche augmentée",
        skills=["Recherche augmentée"],
    )
    db.add(module)
    await db.flush()
    tasks = [
        Task(
            user_id=user_id,
            program_id=program_id,
            module_id=module.id,
            rank=rank,
            title="Projet",
            type="pratiquer",
            minutes=minutes,
            done_criterion="Résultat vérifié",
            planned_date=TODAY,
            status=status,
        )
        for rank, (status, minutes) in enumerate((("todo", 120), ("done", 30)))
    ]
    lesson = Lesson(
        user_id=user_id,
        program_id=program_id,
        module_id=module.id,
        title=module.title,
        status="ready",
        markdown="# Recherche augmentée\nChapitre synthétique.",
    )
    db.add_all([*tasks, lesson])
    return module, lesson


@dataclass(frozen=True)
class DataRefs:
    program_id: str
    module_id: str
    lesson_id: str
    run_id: str


async def seed(app: FastAPI, user_id: str) -> DataRefs:
    async with app.state.session_factory() as db:
        program, module, lesson = await _program(db, user_id)
        python = Skill(user_id=user_id, name="Python", norm_name="python")
        db.add_all(
            [
                python,
                Skill(
                    user_id=user_id,
                    name="Recherche augmentée",
                    norm_name="recherche augmentee",
                    synonyms=["RAG"],
                ),
            ]
        )
        await db.flush()
        db.add(UserSkill(user_id=user_id, skill_id=python.id, level="valide"))
        db.add_all(
            [
                StudySession(
                    user_id=user_id,
                    kind="training",
                    mode="free",
                    status="finished",
                    ended_at=when,
                    minutes=minutes,
                )
                for when, minutes in [
                    (datetime(2026, 10, 18, 23, tzinfo=UTC), 240),  # lundi en France
                    (datetime(2026, 11, 2, 12, tzinfo=UTC), 240),
                    (datetime(2026, 11, 16, 10, tzinfo=UTC), 600),  # semaine en cours
                ]
            ]
        )
        run = _run(user_id, ROLE, 8, [["Python"], ["RAG"], ["RAG", "Python"], ["Finance"]])
        db.add_all(
            [run, _run(user_id, "Data Engineer", 12, [["Python"]]), _run(user_id, ROLE, 14, [])]
        )
        await db.commit()
        return DataRefs(program.id, module.id, lesson.id, run.id)
