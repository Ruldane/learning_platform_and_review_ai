"""DOCX: the zip guard (size, ratio, entries) is rerun before python-docx, which reads in a
thread. python-docx's XML parser does not resolve entities (`resolve_entities=False`)."""

import asyncio
import io
import logging

import docx
from docx.text.paragraph import Paragraph

from app.db.models.memory import DocumentSourceKind
from app.features.memory.service import upload
from app.features.memory.service.sources.base import (
    Extracted,
    ExtractionTools,
    SourceInput,
    read_stored,
    stem,
)

logger = logging.getLogger(__name__)

_HEADING_PREFIXES = ("Heading", "Titre", "Title")


def _is_heading(paragraph: Paragraph) -> bool:
    style = paragraph.style
    name = (style.name if style is not None else None) or ""
    return name.startswith(_HEADING_PREFIXES)


def _read(data: bytes) -> tuple[str | None, str]:
    """Blocking: (title from the properties, otherwise first heading; text of the paragraphs then
    of the tables, one line per row)."""
    document = docx.Document(io.BytesIO(data))
    heading: str | None = None
    lines: list[str] = []
    for paragraph in document.paragraphs:
        text = paragraph.text
        if heading is None and text.strip() and _is_heading(paragraph):
            heading = text.strip()
        lines.append(text)
    for table in document.tables:
        for row in table.rows:
            lines.append("\t".join(cell.text for cell in row.cells))
    title = (document.core_properties.title or "").strip()
    return title or heading, "\n".join(lines)


class DocxSource:
    """Title: document properties, otherwise first heading (`Heading`/`Titre`), otherwise name."""

    kind: DocumentSourceKind = "docx"

    async def extract(self, source: SourceInput, tools: ExtractionTools) -> Extracted:
        data = await read_stored(source, tools)
        upload.check_docx_zip(data)
        try:
            title, text = await asyncio.to_thread(_read, data)
        except Exception as exc:
            # Type only: a parse error message may quote an excerpt of the file.
            logger.info("DOCX %s unreadable (%s)", source.document_id, type(exc).__name__)
            raise upload.docx_invalid() from None
        return Extracted(title=title or stem(source.name), text=text)
