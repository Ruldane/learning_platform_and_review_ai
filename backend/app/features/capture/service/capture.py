"""Quick capture route (SPEC F18, D108): `POST /capture` checks the source then launches the
Archivist's `capture` flow. A single source (otherwise 422 `invalid_input`); a link that is not
http(s): 422 `invalid_url`, fixed message without echo; another user's document: 404
`document_not_found` (a file goes through `POST /documents` first, same ingestion chain, same
size and type guard). No row is written before `launcher.start`: the session itself is the
trace (D66, D72). Logs: ids only, never the address or the text."""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.features.capture.schemas import CaptureRequest, CaptureStarted
from app.features.capture.service.runtime import GRAPH, CaptureRuntime
from app.features.capture.service.store import document_not_found
from app.features.memory.service.captured import document_state
from app.features.memory.service.upload import normalize_url

logger = logging.getLogger(__name__)


def invalid_input() -> AppError:
    return AppError(
        "invalid_input", "Provide a single link, text entry, or document for the capture.", 422
    )


def _given(value: str | None) -> bool:
    return value is not None and bool(value.strip())


async def _payload(db: AsyncSession, user_id: str, body: CaptureRequest) -> dict[str, Any]:
    """The flow's input: a single source, checked."""
    if sum(map(_given, (body.url, body.text, body.document_id))) != 1:
        raise invalid_input()
    if body.url is not None and body.url.strip():
        return {"url": normalize_url(body.url)}
    if body.document_id is not None and body.document_id.strip():
        if await document_state(db, user_id, body.document_id) is None:
            raise document_not_found()
        return {"document_id": body.document_id}
    return {"text": (body.text or "").strip()}


async def start_capture(rt: CaptureRuntime, user_id: str, body: CaptureRequest) -> CaptureStarted:
    async with rt.session_factory() as db:
        payload = await _payload(db, user_id, body)
    session_id = await rt.launcher.start(user_id, GRAPH, payload)
    logger.info(
        "Capture started: user %s, session %s, source %s",
        user_id,
        session_id,
        next(iter(payload)),
    )
    return CaptureStarted(session_id=session_id)
