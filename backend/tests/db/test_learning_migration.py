from datetime import date
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy import delete, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from alembic import command
from app.db.models.learning import Board, Goal, Proposal
from app.db.models.lessons import Lesson, Resource
from app.db.models.program import Module, PlanVersion, Program, Task, Week

BACKEND_DIR = Path(__file__).resolve().parents[2]
LEARNING_TABLES = {
    "goals",
    "proposals",
    "boards",
    "programs",
    "weeks",
    "modules",
    "tasks",
    "lessons",
    "resources",
    "plan_versions",
    "skills",
    "skill_edges",
    "user_skills",
}


def _config(db_file: Path) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_file.as_posix()}")
    return cfg


def _tables(db_file: Path) -> set[str]:
    engine = create_sync_engine(f"sqlite:///{db_file.as_posix()}")
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def _index_names(db_file: Path, table: str) -> set[str]:
    engine = create_sync_engine(f"sqlite:///{db_file.as_posix()}")
    try:
        return {str(i["name"]) for i in inspect(engine).get_indexes(table)}
    finally:
        engine.dispose()


def test_migration_0005_creates_learning_tables(tmp_path: Path) -> None:
    db_file = tmp_path / "app.db"
    command.upgrade(_config(db_file), "head")
    assert _tables(db_file) >= LEARNING_TABLES
    assert "ix_tasks_user_planned" in _index_names(db_file, "tasks")
    assert "ix_tasks_program_id" in _index_names(db_file, "tasks")


def test_migration_0005_downgrade_drops_tables(tmp_path: Path) -> None:
    db_file = tmp_path / "app.db"
    cfg = _config(db_file)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "0004")
    after = _tables(db_file)
    assert not (LEARNING_TABLES & after) and {"sources", "memory_items"} <= after
    command.upgrade(cfg, "head")
    assert _tables(db_file) >= LEARNING_TABLES


async def _program_tree(db: AsyncSession) -> tuple[Goal, Program, Module]:
    goal = Goal(user_id="u1", text="Devenir ingénieure IA")
    db.add(goal)
    await db.flush()
    program = Program(
        user_id="u1",
        goal_id=goal.id,
        title="Parcours",
        start_date=date(2026, 11, 16),
        weekly_minutes=840,
        cap_minutes=714,
    )
    db.add(program)
    await db.flush()
    week = Week(
        user_id="u1",
        program_id=program.id,
        rank=1,
        theme="Bases",
        objective="Installer l'environnement",
        deliverable="Un dépôt",
        start_date=date(2026, 11, 16),
    )
    db.add(week)
    await db.flush()
    module = Module(user_id="u1", week_id=week.id, program_id=program.id, rank=1, title="Python")
    db.add(module)
    await db.flush()
    return goal, program, module


async def test_goal_delete_cascades_to_program_tasks(db_session: AsyncSession) -> None:
    goal, program, module = await _program_tree(db_session)
    db_session.add_all(
        [
            Task(
                user_id="u1",
                module_id=module.id,
                program_id=program.id,
                rank=1,
                title="Lire la doc",
                type="lire",
                minutes=30,
                done_criterion="Notes prises",
                planned_date=date(2026, 11, 16),
            ),
            Lesson(user_id="u1", module_id=module.id, program_id=program.id, title="Python"),
            Resource(
                user_id="u1",
                module_id=module.id,
                program_id=program.id,
                type="article",
                title="Un article",
                url="https://example.test/a",
                url_hash="h1",
            ),
            PlanVersion(user_id="u1", program_id=program.id, version=1, snapshot={}),
        ]
    )
    await db_session.flush()

    await db_session.execute(delete(Goal).where(Goal.id == goal.id))
    await db_session.flush()

    for model in (Program, Week, Module, Task, Lesson, Resource, PlanVersion):
        assert (await db_session.execute(select(model))).first() is None, model.__name__


async def test_proposal_survives_its_board_and_defaults(db_session: AsyncSession) -> None:
    goal = Goal(user_id="u1", text="x")
    db_session.add(goal)
    await db_session.flush()
    assert (goal.status, goal.framing) == ("council", {})
    board = Board(
        user_id="u1", goal_id=goal.id, step=1, kind="comparison", title="t", mermaid="flowchart TD"
    )
    db_session.add(board)
    await db_session.flush()
    proposal = Proposal(
        user_id="u1",
        goal_id=goal.id,
        session_id="s1",
        batch=1,
        rank=1,
        name="Parcours A",
        promise="p",
        duration_weeks=12,
        weekly_hours=10,
        final_project="f",
        board_id=board.id,
    )
    db_session.add(proposal)
    await db_session.flush()

    await db_session.delete(board)
    await db_session.flush()
    await db_session.refresh(proposal)
    assert proposal.board_id is None and proposal.chosen is False


async def test_unique_keys_make_replays_idempotent(db_session: AsyncSession) -> None:
    goal = Goal(user_id="u1", text="x")
    db_session.add(goal)
    await db_session.flush()
    for _ in range(2):
        db_session.add(
            Board(
                user_id="u1",
                goal_id=goal.id,
                step=1,
                kind="domain_map",
                title="t",
                mermaid="m",
                scribe_key="s1:1",
            )
        )
    with pytest.raises(IntegrityError):
        await db_session.flush()
