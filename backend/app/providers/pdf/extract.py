"""Extraction locale du texte d'un PDF avec `pdfplumber` (aucun service externe).

Au chargement, ce module n'importe que `pdfplumber` : le worker en sous-processus (`worker.py`)
l'importe sans tirer FastAPI, dont `PdfUnreadable` hérite par `AppError`. `base` est donc importé
à l'usage (D72)."""

import asyncio
import io
import logging

import pdfplumber

logger = logging.getLogger(__name__)


class PdfPlumberExtractor:
    """Travail bloquant dans un thread, sans délai réel ni plafond de mémoire : la composition
    utilise `SubprocessPdfExtractor`. Les plafonds sont lus à chaque appel dans `base`."""

    async def extract_text(self, data: bytes) -> str:
        from app.providers.pdf import base

        return await asyncio.to_thread(
            extract_pdf_text, data, base.MAX_PDF_PAGES, base.MAX_TEXT_CHARS
        )


def extract_pdf_text(data: bytes, max_pages: int, max_chars: int) -> str:
    """Texte des `max_pages` premières pages, tronqué à `max_chars` ; `PdfUnreadable` sinon."""
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
        error = _unreadable()
    else:
        return "\n".join(parts)[:max_chars]
    raise error from None


def _unreadable() -> Exception:
    from app.providers.pdf.base import PdfUnreadable

    return PdfUnreadable()
