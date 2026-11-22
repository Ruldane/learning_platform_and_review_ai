from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.providers.pdf.base import HtmlPdfRenderer
from app.providers.storage.base import FileStorage


@dataclass(frozen=True)
class BookRuntime:
    session_factory: async_sessionmaker[AsyncSession]
    storage: FileStorage
    renderer: HtmlPdfRenderer
