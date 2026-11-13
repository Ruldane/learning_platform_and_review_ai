"""Lignes des tests de la carte de compétences (D107), écrites directement en base : compétences,
niveaux et preuves, objectif et programme (semaine, modules), leçon, quiz, fiche, relevé.
Aucun LLM, aucun réseau."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.skills import normalize_skill_name
from app.db.models.learning import Goal
from app.db.models.lessons import Lesson
from app.db.models.program import Module, Program, Week
from app.db.models.skills import Skill, SkillEdge, SkillSnapshot, UserSkill
from app.db.models.study import Flashcard, Quiz

Factory = async_sessionmaker[AsyncSession]
API = "/api/v1"
NOW = datetime(2026, 11, 17, 10, 0, tzinfo=UTC)  # mardi, 11 h à Paris
WEEK = date(2026, 11, 16)  # lundi de la semaine de NOW


async def add_skill(
    factory: Factory,
    user_id: str,
    name: str,
    domain: str | None = None,
    level: str | None = None,
    evidence: Sequence[Any] = (),
    synonyms: Sequence[str] = (),
) -> str:
    """Une compétence, avec une ligne de niveau si `level` est donné ; rend son id."""
    async with factory() as db:
        skill = Skill(
            user_id=user_id,
            name=name,
            norm_name=normalize_skill_name(name),
            domain=domain,
            synonyms=list(synonyms),
        )
        db.add(skill)
        await db.flush()
        if level is not None:
            db.add(
                UserSkill(user_id=user_id, skill_id=skill.id, level=level, evidence=list(evidence))
            )
        await db.commit()
        return skill.id


async def add_edge(factory: Factory, user_id: str, before_id: str, after_id: str) -> None:
    async with factory() as db:
        db.add(SkillEdge(user_id=user_id, before_id=before_id, after_id=after_id))
        await db.commit()


async def set_level(factory: Factory, user_id: str, skill_id: str, level: str) -> None:
    async with factory() as db:
        stmt = select(UserSkill).where(UserSkill.user_id == user_id, UserSkill.skill_id == skill_id)
        (await db.execute(stmt)).scalar_one().level = level
        await db.commit()


@dataclass
class ProgramRows:
    goal_id: str
    program_id: str
    modules: list[str]


async def add_goal(
    factory: Factory, user_id: str, *, target_role: str | None = None, created: datetime = NOW
) -> str:
    async with factory() as db:
        goal = Goal(
            user_id=user_id,
            text="Devenir data engineer",
            target_role=target_role,
            framing={},
            status="chosen",
            created_at=created,
        )
        db.add(goal)
        await db.commit()
        return goal.id


async def add_program(
    factory: Factory,
    user_id: str,
    goal_id: str,
    modules: Sequence[tuple[str, Sequence[str]]],
    *,
    status: str = "validated",
    skipped: Sequence[int] = (),
    created: datetime = NOW,
) -> ProgramRows:
    """Un programme d'une semaine ; `modules` : `(titre, compétences)` dans l'ordre."""
    async with factory() as db:
        program = Program(
            user_id=user_id,
            goal_id=goal_id,
            title="Programme données",
            status=status,
            start_date=WEEK,
            weekly_minutes=600,
            cap_minutes=510,
            created_at=created,
        )
        db.add(program)
        await db.flush()
        week = Week(
            user_id=user_id,
            program_id=program.id,
            rank=1,
            theme="Bases",
            objective="Les bases.",
            deliverable="Un carnet.",
            start_date=WEEK,
        )
        db.add(week)
        await db.flush()
        rows = [
            Module(
                user_id=user_id,
                week_id=week.id,
                program_id=program.id,
                rank=rank,
                title=title,
                skills=list(skills),
                skipped=rank in skipped,
            )
            for rank, (title, skills) in enumerate(modules)
        ]
        db.add_all(rows)
        await db.commit()
        return ProgramRows(goal_id, program.id, [row.id for row in rows])


async def add_lesson(
    factory: Factory, user_id: str, rows: ProgramRows, module: int, status: str = "ready"
) -> str:
    async with factory() as db:
        lesson = Lesson(
            user_id=user_id,
            module_id=rows.modules[module],
            program_id=rows.program_id,
            title="Leçon",
            markdown="# Leçon",
            status=status,
        )
        db.add(lesson)
        await db.commit()
        return lesson.id


async def add_quiz(
    factory: Factory, user_id: str, rows: ProgramRows, module: int, status: str = "ready"
) -> str:
    async with factory() as db:
        quiz = Quiz(
            user_id=user_id,
            module_id=rows.modules[module],
            program_id=rows.program_id,
            title="Quiz",
            status=status,
        )
        db.add(quiz)
        await db.commit()
        return quiz.id


async def add_card(factory: Factory, user_id: str, skill: str | None, due: date) -> None:
    async with factory() as db:
        db.add(
            Flashcard(
                user_id=user_id,
                front=f"Recto {skill} {due}",
                back="Verso",
                front_hash=f"{skill}-{due}",
                skill=skill,
                source="quiz",
                due_date=due,
            )
        )
        await db.commit()


async def add_snapshot(factory: Factory, user_id: str, week: date, levels: dict[str, str]) -> None:
    async with factory() as db:
        db.add(SkillSnapshot(user_id=user_id, week_start=week, levels=levels))
        await db.commit()
