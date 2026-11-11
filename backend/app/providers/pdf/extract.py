"""Extraction locale du texte d'un PDF avec `pdfplumber` (aucun service externe)."""

import asyncio
import io
import logging

import pdfplumber

from app.providers.pdf import base
from app.providers.pdf.base import PdfUnreadable

logger = logging.getLogger(__name__)


class PdfPlumberExtractor:
    """Travail bloquant dans un thread. Les plafonds sont lus à chaque appel dans `base`."""

    async def extract_text(self, data: bytes) -> str:
        return await asyncio.to_thread(_extract, data, base.MAX_PDF_PAGES, base.MAX_TEXT_CHARS)


def _extract(data: bytes, max_pages: int, max_chars: int) -> str:
    try:
        # `pages` évite de construire les pages au-delà du plafond.
        with pdfplumber.open(io.BytesIO(data), pages=list(range(1, max_pages + 1))) as pdf:
            parts: list[str] = []
            size = 0
            for page in pdf.pages:
                text = page.extract_text() or ""
                page.close()
                parts.append(text)
                size += len(text) + 1
                if size >= max_chars:
                    break
    except Exception as exc:
        # Type seul : le message d'une exception de pdfminer peut citer un extrait du fichier.
        logger.info("PDF illisible (%s)", type(exc).__name__)
        raise PdfUnreadable() from None
    return "\n".join(parts)[:max_chars]
