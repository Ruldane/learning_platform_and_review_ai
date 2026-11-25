"""Local text extraction from a PDF with `pdfplumber` (no external service).

At load time, this module imports only `pdfplumber`: the subprocess worker (`worker.py`) imports
it without pulling in FastAPI (`PdfUnreadable` inherits from `AppError`, which needs it). `base`
is therefore imported at use (D72)."""

import asyncio
import io
import logging

import pdfplumber

logger = logging.getLogger(__name__)


class PdfPlumberExtractor:
    """Blocking work in a thread, with no real deadline nor memory cap: the composition uses
    `SubprocessPdfExtractor`. The caps are read at each call in `base`."""

    async def extract_text(self, data: bytes) -> str:
        from app.providers.pdf import base

        return await asyncio.to_thread(
            extract_pdf_text, data, base.MAX_PDF_PAGES, base.MAX_TEXT_CHARS
        )


def extract_pdf_text(data: bytes, max_pages: int, max_chars: int) -> str:
    """Text of the first `max_pages` pages, truncated to `max_chars`; `PdfUnreadable` otherwise."""
    try:
        # `pages` avoids building the pages beyond the cap.
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
        # Type only: the message of a pdfminer exception can quote an extract of the file.
        logger.info("PDF illisible (%s)", type(exc).__name__)
        error = _unreadable()
    else:
        return "\n".join(parts)[:max_chars]
    raise error from None


def _unreadable() -> Exception:
    from app.providers.pdf.base import PdfUnreadable

    return PdfUnreadable()
