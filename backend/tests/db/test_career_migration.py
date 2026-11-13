"""Migration 0008 (6.2) : tables de la carrière, index partiels, cascades, retour arrière."""

from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy import delete, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from alembic import command
from app.db.models.career import CvModification, CvReview, CvTemplate, CvVersion, MasterProfile
from app.db.models.postings import JobPosting

BACKEND_DIR = Path(__file__).resolve().parents[2]
CAREER_TABLES = {
    "master_profile",
    "cv_templates",
    "job_postings",
    "companies",
    "cv_reviews",
    "cv_modifications",
    "cv_versions",
}


def _config(db_file: Path) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_file.as_posix()}")
    return cfg


def _inspect(db_file: Path, call: str, *args: str) -> list[dict[str, object]]:
    engine = create_sync_engine(f"sqlite:///{db_file.as_posix()}")
    try:
        result: list[dict[str, object]] = getattr(inspect(engine), call)(*args)
        return result
    finally:
        engine.dispose()


def _tables(db_file: Path) -> set[str]:
    engine = create_sync_engine(f"sqlite:///{db_file.as_posix()}")
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def _indexes(db_file: Path, table: str) -> set[str]:
    return {str(i["name"]) for i in _inspect(db_file, "get_indexes", table)}


def _index_sql(db_file: Path) -> dict[str, str]:
    engine = create_sync_engine(f"sqlite:///{db_file.as_posix()}")
    try:
        with engine.connect() as conn:
            rows = conn.execute(text("SELECT name, sql FROM sqlite_master WHERE type = 'index'"))
            return {str(row[0]): str(row[1]) for row in rows}
    finally:
        engine.dispose()


def test_migration_0008_creates_career_tables(tmp_path: Path) -> None:
    db_file = tmp_path / "app.db"
    command.upgrade(_config(db_file), "head")
    assert _tables(db_file) >= CAREER_TABLES
    assert {
        "uq_job_postings_url",
        "uq_job_postings_text",
        "ix_job_postings_company_title",
    } <= _indexes(db_file, "job_postings")
    assert "uq_cv_templates_active" in _indexes(db_file, "cv_templates")
    assert "ix_cv_versions_user_review" in _indexes(db_file, "cv_versions")
    columns = {str(c["name"]) for c in _inspect(db_file, "get_columns", "master_profile")}
    assert {"data", "document_ids", "dropped", "version", "status", "source"} <= columns


def test_migration_0008_partial_indexes_are_unique(tmp_path: Path) -> None:
    db_file = tmp_path / "app.db"
    command.upgrade(_config(db_file), "head")
    sql = _index_sql(db_file)
    for name, where in (
        ("uq_job_postings_url", "WHERE url_norm IS NOT NULL"),
        ("uq_job_postings_text", "WHERE url_norm IS NULL"),
        ("uq_cv_templates_active", "WHERE active = 1"),
    ):
        assert sql[name].startswith("CREATE UNIQUE INDEX") and where in sql[name], name


def test_migration_0008_downgrade(tmp_path: Path) -> None:
    db_file = tmp_path / "app.db"
    cfg = _config(db_file)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "0007")
    after = _tables(db_file)
    assert not (CAREER_TABLES & after) and {"llm_calls", "journal_entries"} <= after
    command.upgrade(cfg, "head")
    assert _tables(db_file) >= CAREER_TABLES


def _posting(user_id: str = "u1", url_norm: str | None = None, text_hash: str = "h1") -> JobPosting:
    return JobPosting(
        user_id=user_id,
        url=url_norm,
        url_norm=url_norm,
        source="url" if url_norm else "text",
        text="Offre fictive",
        text_hash=text_hash,
    )


async def test_same_url_norm_twice_violates_index(db_session: AsyncSession) -> None:
    url = "https://exemple.org/jobs/42"
    # Autre utilisateur, ou même texte collé sans lien : permis.
    db_session.add_all([_posting(url_norm=url), _posting("u2", url), _posting(text_hash="h2")])
    await db_session.flush()
    db_session.add(_posting(url_norm=url, text_hash="h3"))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_same_pasted_text_twice_violates_index(db_session: AsyncSession) -> None:
    # Un lien de même empreinte ne compte pas : seul le texte collé (sans lien) est unique.
    db_session.add_all([_posting(), _posting(url_norm="https://exemple.org/a"), _posting("u2")])
    await db_session.flush()
    db_session.add(_posting())
    with pytest.raises(IntegrityError):
        await db_session.flush()


def _template(active: bool, user_id: str = "u1") -> CvTemplate:
    return CvTemplate(
        user_id=user_id,
        document_id="d1",
        name="Mon CV",
        active=active,
        page_count=1,
        page_size={"width_pt": 595.0, "height_pt": 842.0},
        selectable=True,
    )


async def test_two_active_templates_violate_index(db_session: AsyncSession) -> None:
    db_session.add_all([_template(True), _template(False), _template(False), _template(True, "u2")])
    await db_session.flush()
    first = (await db_session.execute(select(CvTemplate))).scalars().first()
    assert first is not None and (first.status, first.passes, first.fonts) == ("capturing", 0, [])
    db_session.add(_template(True))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_posting_delete_cascades_to_review_tree(db_session: AsyncSession) -> None:
    posting = _posting()
    db_session.add(posting)
    await db_session.flush()
    review = CvReview(user_id="u1", posting_id=posting.id, template_id="t1", profile_version=1)
    db_session.add(review)
    await db_session.flush()
    db_session.add_all(
        [
            CvModification(
                user_id="u1",
                review_id=review.id,
                ref="m1",
                section="experience",
                action="rewrite",
                before="a",
                after="b",
                reason="r",
                type="clarity",
                status="proposed",
                author="recruiter",
            ),
            CvVersion(
                user_id="u1",
                review_id=review.id,
                posting_id=posting.id,
                template_id="t1",
                number=1,
                content={"name": "Camille Exemple"},
                filename="CV_Camille_Exemple.pdf",
                original_page_count=1,
            ),
        ]
    )
    await db_session.flush()
    assert review.status == "running"

    await db_session.execute(delete(JobPosting).where(JobPosting.id == posting.id))
    await db_session.flush()
    for model in (CvReview, CvModification, CvVersion):
        assert (await db_session.execute(select(model))).first() is None, model.__name__


async def test_profile_version_is_unique_per_user(db_session: AsyncSession) -> None:
    def profile(user_id: str) -> MasterProfile:
        return MasterProfile(user_id=user_id, version=1, data={}, source="archivist")

    db_session.add_all([profile("u1"), profile("u2")])
    await db_session.flush()
    stored = (await db_session.execute(select(MasterProfile))).scalars().first()
    assert stored is not None and (stored.status, stored.dropped) == ("draft", [])
    db_session.add(profile("u1"))
    with pytest.raises(IntegrityError):
        await db_session.flush()
