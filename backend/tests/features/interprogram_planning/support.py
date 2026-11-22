"""Programmes validés et réservation horaire synthétiques pour une semaine commune."""

from datetime import UTC, date, datetime, time, timedelta

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import new_id, utcnow
from app.db.models.calendar import CalendarProposal
from app.db.models.learning import Goal
from app.db.models.program import Module, Program, Task, Week

MONDAY = date(2030, 1, 7)
FUNDAMENTALS = "Standardiser les entrées"
APPLICATION = "Analyser un relevé"


async def _seed_program(db: AsyncSession, owner: str, title: str, status: str) -> Program:
    goal = Goal(user_id=owner, text=title, target_role="Analyste", status="planned")
    db.add(goal)
    await db.flush()
    program = Program(
        user_id=owner,
        goal_id=goal.id,
        status=status,
        title=title,
        start_date=MONDAY,
        weekly_minutes=120,
        cap_minutes=102,
    )
    db.add(program)
    await db.flush()
    return program


async def seed_task(
    db: AsyncSession,
    owner: str,
    title: str,
    minutes: int,
    *,
    prerequisites: tuple[str, ...] = (),
    status: str = "validated",
) -> tuple[str, str]:
    program = await _seed_program(db, owner, title, status)
    week = Week(
        user_id=owner,
        program_id=program.id,
        rank=1,
        theme=title,
        objective=title,
        deliverable="Résultat observé",
        start_date=MONDAY,
    )
    db.add(week)
    await db.flush()
    module = Module(
        user_id=owner,
        program_id=program.id,
        week_id=week.id,
        rank=0,
        title=title,
        skills=[title],
        prerequisites=list(prerequisites),
    )
    db.add(module)
    await db.flush()
    item = Task(
        user_id=owner,
        program_id=program.id,
        module_id=module.id,
        rank=0,
        title=title,
        type="pratiquer",
        minutes=minutes,
        done_criterion="Résultat vérifié",
        planned_date=MONDAY,
    )
    db.add(item)
    await db.flush()
    return program.id, item.id


def seed_booking(db: AsyncSession, owner: str) -> None:
    start = datetime.combine(MONDAY, time(7), UTC)
    end = datetime.combine(MONDAY, time(20), UTC)
    event = CalendarProposal(
        user_id=owner,
        connection_generation=new_id(),
        event_id=new_id(),
        source_hash="fixture",
        starts_at=start,
        expires_at=start + timedelta(days=1),
        synced_at=utcnow(),
        payload={
            "preview": {
                "start": start.isoformat(),
                "end": end.isoformat(),
                "kind": "interview",
                "timezone": "Europe/Paris",
            }
        },
    )
    db.add(event)


async def seed_week(app: FastAPI, user_id: str | None = None) -> tuple[list[str], list[str]]:
    owner = user_id or app.state.local_user_id
    async with app.state.session_factory() as db:
        first = await seed_task(db, owner, FUNDAMENTALS, 45)
        second = await seed_task(db, owner, APPLICATION, 45, prerequisites=(FUNDAMENTALS,))
        fixed = await seed_task(db, owner, "Déjà prévu", 30)
        seed_booking(db, owner)
        await db.commit()
    return [first[0], second[0]], [first[1], second[1], fixed[1]]


async def dates(app: FastAPI, tasks: list[str]) -> list[date]:
    async with app.state.session_factory() as db:
        result = []
        for task_id in tasks:
            task = await db.get(Task, task_id)
            assert task is not None
            result.append(task.planned_date)
        return result
