"""Local copy of a freely downloadable PDF (SPEC 3.6, D91): a lesson resource whose address
returns a PDF is kept on disk, otherwise it stays a link and a reading card.

The download goes through the research's safe fetcher (SSRF guard: public addresses over
http(s) only, each redirect re-checked, 20 MB at most, 15 s) and asks for ONLY the
`application/pdf` type. A domain excluded in the settings is never contacted. Any error
returns `None`; logs: ids and code only, never the address (SPEC 17.2)."""

import logging
from urllib.parse import urlsplit

from app.core.errors import AppError
from app.features.research.service.domains import host_matches
from app.features.research.service.prefs import load_prefs
from app.features.research.service.runtime import ResearchRuntime

logger = logging.getLogger(__name__)

PDF_TYPES = ("application/pdf",)
MAX_PDF_BYTES = 20 * 1024 * 1024
_PDF_MAGIC = b"%PDF-"


async def _excluded(runtime: ResearchRuntime, user_id: str, url: str) -> bool:
    async with runtime.session_factory() as db:
        prefs = await load_prefs(db, user_id)
    try:
        host = urlsplit(url).hostname or ""
    except ValueError:
        return True
    return any(host_matches(host, domain) for domain in prefs.excluded)


async def download_pdf(runtime: ResearchRuntime, user_id: str, url: str) -> bytes | None:
    """The PDF at `url` (20 MB at most, `%PDF-` signature checked), `None` otherwise: excluded
    domain, address refused by the guard, other content type, unreadable page, file too big."""
    if await _excluded(runtime, user_id, url):
        logger.info("PDF not downloaded (user %s): excluded domain", user_id)
        return None
    try:
        fetched = await runtime.providers.fetcher.fetch(url, content_types=PDF_TYPES)
    except AppError as exc:
        logger.info("PDF not downloaded (user %s): %s", user_id, exc.code)
        return None
    except Exception as exc:  # raw message never logged (it could quote the address)
        logger.warning("PDF not downloaded (user %s): %s", user_id, type(exc).__name__)
        return None
    body = fetched.body
    if len(body) > MAX_PDF_BYTES or not body.startswith(_PDF_MAGIC):
        logger.info("PDF not downloaded (user %s): content refused", user_id)
        return None
    return body
