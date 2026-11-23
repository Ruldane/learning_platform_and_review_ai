from pathlib import Path

from sqlalchemy import Connection, create_engine, text

from alembic import command
from tests.db.test_study_migration import _config


def test_chat_upgrade_backfills_title_and_activity_without_replacing_legacy_ids(
    tmp_path: Path,
) -> None:
    db_file = tmp_path / "legacy-chat.db"
    config = _config(db_file)
    command.upgrade(config, "0071")
    engine = create_engine(f"sqlite:///{db_file.as_posix()}")
    try:
        with engine.begin() as db:
            db.execute(
                text(
                    "INSERT INTO conversations (id, user_id, scope, subject_id, created_at, "
                    "updated_at) VALUES ('ancien-fil', 'u1', 'brain', 'u1', :day, :day)"
                ),
                {"day": "2026-11-18 09:00:00"},
            )
            for rank, question in enumerate(("Première question", "Question suivante"), start=1):
                _insert_turn(db, rank, question)
        command.upgrade(config, "0071a")
        with engine.connect() as db:
            row = db.execute(
                text("SELECT id, title, lesson_ids, updated_at FROM conversations")
            ).one()
            assert tuple(row) == (
                "ancien-fil",
                "Première question",
                "[]",
                "2026-11-18 09:02:00",
            )
            turns = db.execute(
                text("SELECT id, thread_id, question, answer FROM conversation_turns ORDER BY id")
            ).all()
            assert [tuple(turn) for turn in turns] == [
                ("tour-1", "ancien-fil", "Première question", "Réponse 1"),
                ("tour-2", "ancien-fil", "Question suivante", "Réponse 2"),
            ]
        command.downgrade(config, "0071")
        with engine.connect() as db:
            assert db.scalar(text("SELECT count(*) FROM conversation_turns")) == 2
    finally:
        engine.dispose()


def _insert_turn(db: Connection, rank: int, question: str) -> None:
    session_id = f"session-{rank}"
    day = f"2026-11-18 09:0{rank}:00"
    db.execute(
        text(
            "INSERT INTO sessions (id, user_id, created_at, updated_at, graph, status, input, "
            "tokens_in, tokens_out, cost_usd) "
            "VALUES (:session_id, 'u1', :day, :day, 'conversation', 'completed', '{}', 0, 0, 0.0)"
        ),
        {"session_id": session_id, "day": day},
    )
    db.execute(
        text(
            "INSERT INTO conversation_turns (id, user_id, created_at, updated_at, thread_id, "
            "request_id, session_id, question, strong, answer, sources) "
            "VALUES (:id, 'u1', :day, :day, 'ancien-fil', :id, :session_id, "
            ":question, 0, :answer, '[]')"
        ),
        {
            "id": f"tour-{rank}",
            "day": day,
            "session_id": session_id,
            "question": question,
            "answer": f"Réponse {rank}",
        },
    )
