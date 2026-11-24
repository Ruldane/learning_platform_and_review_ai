"""Skill level migration keeps evidence, study names and undo records readable."""

from datetime import date
from pathlib import Path

from alembic.config import Config
from sqlalchemy import Connection, Table, create_engine, select

from alembic import command
from app.db.models.mcp import McpChange
from app.db.models.memory import MemoryItem
from app.db.models.skills import Skill, SkillSnapshot, UserSkill
from app.db.models.study import StudySession

EVIDENCE = [{"kind": "quiz", "label": "Quiz validé"}]
SKILL_META = {"level": "proven", "reason": "Le niveau « prouve » a été vérifié."}
OLD_META = {**SKILL_META, "level": "prouve"}
OLD_OUTCOME = {"result": {"skills": [["valide", "en_cours"]]}}
OUTCOME = {"result": {"skills": [["valide", "in_progress"]]}}


def _insert(conn: Connection, table: Table, row_id: str, **fields: object) -> None:
    conn.execute(table.insert().values(id=row_id, user_id="u1", **fields))


def _seed(conn: Connection) -> None:
    _insert(conn, Skill.__table__, "s1", name="SQL", norm_name="sql")
    _insert(conn, UserSkill.__table__, "us1", skill_id="s1", level="prouve", evidence=EVIDENCE)
    _insert(
        conn,
        SkillSnapshot.__table__,
        "snapshot",
        week_start=date(2026, 11, 23),
        levels={"s1": "valide"},
    )
    _insert(
        conn,
        StudySession.__table__,
        "study",
        kind="training",
        mode="direct",
        status="finished",
        outcome=OLD_OUTCOME,
        summary="Bien joué.",
    )
    _insert(
        conn,
        MemoryItem.__table__,
        "memory",
        kind="acquis",
        title="SQL",
        text="Requête validée.",
        created_by="user",
        meta=OLD_META,
        content_hash="skill-fingerprint",
    )


def _seed_history(conn: Connection) -> None:
    for name, row, snapshot in (
        ("user_skills", "us1", {"level": "prouve", "evidence": EVIDENCE}),
        ("memory_items", "memory", {"kind": "acquis", "meta": OLD_META}),
        ("skill_snapshots", "snapshot", {"levels": {"s1": "valide"}}),
        ("study_sessions", "study", {"outcome": OLD_OUTCOME}),
    ):
        _insert(
            conn,
            McpChange.__table__,
            name,
            call_id="call",
            table_name=name,
            row_id=row,
            op="update",
            before=snapshot,
            after=snapshot,
        )


def _state(conn: Connection) -> tuple[object, ...]:
    skill = conn.execute(select(UserSkill.level, UserSkill.evidence)).one()
    history = conn.execute(select(SkillSnapshot.levels)).scalar_one()
    study = conn.execute(select(StudySession.outcome, StudySession.summary)).one()
    memory = conn.execute(select(MemoryItem.meta, MemoryItem.text)).one()
    changes = conn.execute(select(McpChange.table_name, McpChange.before, McpChange.after)).all()
    return skill, history, study, memory, {name: (before, after) for name, before, after in changes}


def test_skill_levels_are_renamed_in_records_and_undo_snapshots(tmp_path: Path) -> None:
    db_file = tmp_path / "app.db"
    cfg = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_file.as_posix()}")
    command.upgrade(cfg, "0084")
    engine = create_engine(f"sqlite:///{db_file.as_posix()}")
    try:
        with engine.begin() as conn:
            _seed(conn)
            _seed_history(conn)
            original = _state(conn)
        command.upgrade(cfg, "0085")
        snapshots = {
            "user_skills": {"level": "proven", "evidence": EVIDENCE},
            "memory_items": {"kind": "acquis", "meta": SKILL_META},
            "skill_snapshots": {"levels": {"s1": "validated"}},
            "study_sessions": {"outcome": OUTCOME},
        }
        with engine.connect() as conn:
            assert _state(conn) == (
                ("proven", EVIDENCE),
                {"s1": "validated"},
                (OUTCOME, "Bien joué."),
                (SKILL_META, "Requête validée."),
                {name: (content, content) for name, content in snapshots.items()},
            )
        command.downgrade(cfg, "0084")
        with engine.connect() as conn:
            assert _state(conn) == original
    finally:
        engine.dispose()
