"""Créer le notebook et la leçon dans la même transaction."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.tools.paper_lab_port import ArticleSource, PaperDraft, PaperLabContext, cited_course
from app.core.caller import Caller
from app.core.errors import AppError
from app.db.models.paper_lab import PaperLab
from app.features.ide.service import IdeService
from app.features.paper_lab.repository import PaperLabRepository
from app.features.paper_lab.service.notebooks import notebook_files


async def _assigned(db: AsyncSession, user_id: str, lab_id: str, session_id: str) -> PaperLab:
    row = await PaperLabRepository(db, user_id).require(lab_id)
    if row.session_id != session_id:
        raise AppError("paper_lab_changed", "La session de préparation a changé.", 409)
    return row


class AgentPaperLabStore:
    def __init__(self, factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = factory

    async def context(self, user_id: str, lab_id: str, session_id: str) -> PaperLabContext:
        async with self._factory() as db:
            row = await _assigned(db, user_id, lab_id, session_id)
            return PaperLabContext(row.url, row.stage == "ready")

    async def publish(
        self, user_id: str, lab_id: str, session_id: str, source: ArticleSource, draft: PaperDraft
    ) -> None:
        async with self._factory() as db:
            row = await _assigned(db, user_id, lab_id, session_id)
            if not await PaperLabRepository(db, user_id).claim_publication(row):
                return
            course = cited_course(source, draft)
            files = notebook_files(source.url, draft.experiment)
            ide = IdeService(db, user_id, None, Caller("app", "papier-au-code"))
            project = await ide.open_session(title=draft.title)
            await ide.save_files(project.id, files, entry="main.py")
            row.url = source.url
            row.source_title = source.title[:240]
            row.title = draft.title
            row.course = course
            row.expected = draft.experiment.expected
            row.ide_session_id = project.id
            await db.commit()
