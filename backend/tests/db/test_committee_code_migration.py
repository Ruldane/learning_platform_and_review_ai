"""The hiring panel rename preserves past votes, dossier prose, and undo history."""

from pathlib import Path

from alembic.config import Config
from sqlalchemy import Connection, create_engine, select

from alembic import command
from app.agents.tools.committee_schema import Vote
from app.db.models.applications import CommitteeRun
from app.db.models.mcp import McpChange
from app.db.models.postings import Company


def _dossier(size: str) -> dict[str, str]:
    return {"size": size, "product": "Un produit testé. [1]"}


def _result(verdict: str, votes: tuple[str, ...]) -> dict[str, object]:
    return {
        "verdict": verdict,
        "votes": [{"vote": vote, "objection": "Profil trop général."} for vote in votes],
    }


def _seed(conn: Connection) -> None:
    dossier = _dossier("pme")
    result = _result("peut_etre", ("oui", "non", "peut_etre"))
    conn.execute(
        Company.__table__.insert().values(
            id="company", user_id="u1", name="Acme", name_norm="acme", dossier=dossier
        )
    )
    conn.execute(
        CommitteeRun.__table__.insert().values(
            id="panel",
            user_id="u1",
            cv_version_id="cv",
            posting_id="posting",
            session_id="session",
            status="done",
            **result,
        )
    )
    for table, row, before in (
        ("companies", "company", {"dossier": dossier}),
        ("committee_runs", "panel", result),
    ):
        conn.execute(
            McpChange.__table__.insert().values(
                id=row,
                user_id="u1",
                call_id="call",
                table_name=table,
                row_id=row,
                op="update",
                before=before,
                after=before,
            )
        )


def _read(conn: Connection) -> tuple[object, object, object]:
    company = conn.execute(select(Company.dossier)).scalar_one()
    committee = conn.execute(select(CommitteeRun.verdict, CommitteeRun.votes)).one()
    snapshots = conn.execute(select(McpChange.before, McpChange.after).order_by(McpChange.id)).all()
    return company, committee, snapshots


def test_panel_codes_migrate_and_downgrade_with_undo(tmp_path: Path) -> None:
    db_file = tmp_path / "app.db"
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_file.as_posix()}")
    command.upgrade(config, "0088")
    engine = create_engine(f"sqlite:///{db_file.as_posix()}")
    try:
        with engine.begin() as conn:
            _seed(conn)
            original = _read(conn)
        command.upgrade(config, "0089")
        dossier = _dossier("sme")
        result = _result("maybe", ("yes", "no", "maybe"))
        with engine.connect() as conn:
            assert _read(conn) == (
                dossier,
                ("maybe", result["votes"]),
                [({"dossier": dossier}, {"dossier": dossier}), (result, result)],
            )
        command.downgrade(config, "0088")
        with engine.connect() as conn:
            assert _read(conn) == original
    finally:
        engine.dispose()


def test_legacy_played_vote_can_be_resumed() -> None:
    vote = Vote.model_validate(
        {"vote": "peut_etre", "objection": "Profil", "reason": "Trop vague."}
    )
    assert vote.vote == "maybe"
