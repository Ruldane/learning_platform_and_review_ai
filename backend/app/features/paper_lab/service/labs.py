"""Lancer la Fabrique depuis un article et relire les résultats."""

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runtime.launcher import SessionLauncher
from app.agents.tools.paper_lab_port import PAPER_GRAPH
from app.db.models.paper_lab import PaperLab, PaperStage
from app.features.paper_lab.repository import PaperLabRepository
from app.features.paper_lab.schemas import PaperLabOut, PaperLabStarted, PaperLabSummary
from app.features.sessions.service import session_facts

_FAILED = {"failed", "cancelled", "expired"}


async def start_lab(launcher: SessionLauncher, user_id: str, url: str) -> PaperLabStarted:
    lab_id = str(uuid4())

    async def prepare(db: AsyncSession, session_id: str) -> None:
        db.add(PaperLab(id=lab_id, user_id=user_id, url=url, session_id=session_id, stage="queued"))

    session_id = await launcher.start(
        user_id,
        PAPER_GRAPH,
        {"lab_id": lab_id},
        subject_type=PAPER_GRAPH,
        subject_id=lab_id,
        prepare=prepare,
    )
    return PaperLabStarted(lab_id=lab_id, session_id=session_id)


async def _summary(db: AsyncSession, user_id: str, row: PaperLab) -> PaperLabSummary:
    stage: PaperStage = row.stage
    if stage == "queued":
        facts = await session_facts(db, user_id, row.session_id)
        if facts is not None and facts.status in _FAILED:
            return PaperLabSummary(id=row.id, url=row.url, title=row.title, stage="failed")
    return PaperLabSummary(id=row.id, url=row.url, title=row.title, stage=stage)


async def list_labs(db: AsyncSession, user_id: str) -> list[PaperLabSummary]:
    rows = await PaperLabRepository(db, user_id).list()
    return [await _summary(db, user_id, row) for row in rows]


async def read_lab(db: AsyncSession, user_id: str, lab_id: str) -> PaperLabOut:
    row = await PaperLabRepository(db, user_id).require(lab_id)
    summary = await _summary(db, user_id, row)
    return PaperLabOut(
        **summary.model_dump(),
        source_title=row.source_title,
        course=row.course,
        expected=row.expected,
        ide_session_id=row.ide_session_id,
        session_id=row.session_id,
    )
