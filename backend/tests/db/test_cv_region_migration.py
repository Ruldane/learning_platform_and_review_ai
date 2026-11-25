"""Keep stored CV comparison measurements and undo data across the region rename."""

from pathlib import Path
from typing import Any

from alembic.config import Config
from sqlalchemy import Connection, create_engine, select

from alembic import command
from app.db.models.career import CvTemplate
from app.db.models.mcp import McpChange
from app.features.cv.schemas_templates import ZoneDiffOut
from app.features.cv.service.templates_data import similarity_from_json


def _comparison(top: str, left: str) -> dict[str, Any]:
    return {
        "score": 88,
        "ink": 0.9,
        "text": 0.8,
        "color": 1.0,
        "pages_original": 1,
        "pages_render": 1,
        "zones": [{"zone": left, "original": 0.4, "render": 0.3}],
        "matches": [{"zone": top, "ink": 0.8, "text": 0.9}],
        "shifts": {top: 8},
    }


def _stored(top: str, left: str) -> dict[str, Any]:
    detail = _comparison(top, left)
    return {
        "score_detail": detail,
        "pass_log": [
            {"pass_no": 1, "score": 88, "similarity": detail, "note": "Marge en haut"},
            {"pass_no": 2, "score": 90, "similarity": detail, "render_pages": ["page.png"]},
        ],
    }


def _seed(conn: Connection) -> None:
    before = _stored("haut", "gauche")
    conn.execute(
        CvTemplate.__table__.insert().values(
            id="template",
            user_id="owner",
            document_id="cv",
            name="Gabarit",
            selectable=True,
            page_count=1,
            page_size={"width_pt": 612, "height_pt": 792},
            **before,
        )
    )
    conn.execute(
        McpChange.__table__.insert().values(
            id="change",
            user_id="owner",
            call_id="call",
            table_name="cv_templates",
            row_id="template",
            op="update",
            before=before,
            after=before,
        )
    )


def _assert_stored(conn: Connection, top: str, left: str) -> None:
    expected = _stored(top, left)
    current = conn.execute(select(CvTemplate.score_detail, CvTemplate.pass_log)).one()
    undo = conn.execute(select(McpChange.before, McpChange.after)).one()
    assert current == (expected["score_detail"], expected["pass_log"])
    assert undo == (expected, expected)


def test_rename_cv_regions_in_comparisons_pass_history_and_undo(tmp_path: Path) -> None:
    database = tmp_path / "app.db"
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{database.as_posix()}")
    command.upgrade(config, "0089")
    engine = create_engine(f"sqlite:///{database.as_posix()}")
    try:
        with engine.begin() as conn:
            _seed(conn)
        command.upgrade(config, "0090")
        with engine.connect() as conn:
            _assert_stored(conn, "top", "left")
        command.downgrade(config, "0089")
        with engine.connect() as conn:
            _assert_stored(conn, "haut", "gauche")
    finally:
        engine.dispose()


def test_read_saved_comparison_with_legacy_codes() -> None:
    data = _comparison("haut", "gauche")
    comparison = similarity_from_json(data)
    assert comparison.zones[0].zone == "left"
    assert comparison.matches[0].zone == "top"
    assert comparison.shifts == {"top": 8}
    assert ZoneDiffOut.model_validate(data["zones"][0]).zone == "left"
