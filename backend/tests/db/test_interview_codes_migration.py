"""Persisted interview transcripts and score values survive a code migration."""

from pathlib import Path

from alembic.config import Config
from sqlalchemy import Connection, create_engine, select

from alembic import command
from app.db.models.applications import Interview
from app.db.models.mcp import McpChange

EXCHANGES_BEFORE = [
    {"criterion": "clarte", "source": "offre", "question": "Pourquoi ce poste ?"},
    {"criterion": "profondeur", "source": "dossier", "question": "Comment l’as-tu testé ?"},
    {"criterion": "adequation", "source": "ecart", "question": "Donne un exemple."},
]
EXCHANGES_AFTER = [
    {"criterion": "clarity", "source": "posting", "question": "Pourquoi ce poste ?"},
    {
        "criterion": "technical_depth",
        "source": "company_dossier",
        "question": "Comment l’as-tu testé ?",
    },
    {"criterion": "role_fit", "source": "gap", "question": "Donne un exemple."},
]
DEBRIEF_BEFORE = {
    "scores": {"clarte": 5, "structure": 2, "profondeur_technique": 4, "adequation": 3},
    "strengths": ["Exemple précis et chiffré."],
}
DEBRIEF_AFTER = {
    "scores": {"clarity": 5, "structure": 2, "technical_depth": 4, "role_fit": 3},
    "strengths": ["Exemple précis et chiffré."],
}


def _seed(conn: Connection) -> None:
    before = {"exchanges": EXCHANGES_BEFORE, "debrief": DEBRIEF_BEFORE}
    conn.execute(
        Interview.__table__.insert().values(
            id="interview",
            user_id="u1",
            session_id="session",
            mode="mixed",
            duration_min=15,
            language="fr",
            status="done",
            **before,
        )
    )
    conn.execute(
        McpChange.__table__.insert().values(
            id="change",
            user_id="u1",
            call_id="call",
            table_name="interviews",
            row_id="interview",
            op="update",
            before=before,
            after=before,
        )
    )


def _read(conn: Connection) -> tuple[object, object]:
    interview = conn.execute(
        select(Interview.exchanges, Interview.debrief, Interview.language)
    ).one()
    change = conn.execute(select(McpChange.before, McpChange.after)).one()
    return interview, change


def test_interview_codes_preserve_transcripts_scores_and_undo(tmp_path: Path) -> None:
    db_file = tmp_path / "app.db"
    cfg = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_file.as_posix()}")
    command.upgrade(cfg, "0086")
    engine = create_engine(f"sqlite:///{db_file.as_posix()}")
    try:
        with engine.begin() as conn:
            _seed(conn)
            original = _read(conn)
        command.upgrade(cfg, "0087")
        after = {"exchanges": EXCHANGES_AFTER, "debrief": DEBRIEF_AFTER}
        with engine.connect() as conn:
            assert _read(conn) == ((EXCHANGES_AFTER, DEBRIEF_AFTER, "fr"), (after, after))
        command.downgrade(cfg, "0086")
        with engine.connect() as conn:
            assert _read(conn) == original
    finally:
        engine.dispose()
