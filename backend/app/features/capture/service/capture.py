"""Route de la capture rapide (SPEC F18, D108) : `POST /capture` contrôle la source puis lance le
parcours `capture` de l'Archiviste. Une seule source (sinon 422 `invalid_input`) ; un lien qui
n'est pas http(s) : 422 `invalid_url`, message fixe sans recopie ; le document d'une autre :
404 `document_not_found` (un fichier passe d'abord par `POST /documents`, même chaîne
d'ingestion, même garde de taille et de type). Aucune ligne n'est écrite avant
`launcher.start` : la session elle-même est la trace (D66, D72). Journaux : identifiants
seulement, jamais l'adresse ni le texte."""

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
        "invalid_input", "Une capture demande une seule source : lien, texte ou document.", 422
    )


def _given(value: str | None) -> bool:
    return value is not None and bool(value.strip())


async def _payload(db: AsyncSession, user_id: str, body: CaptureRequest) -> dict[str, Any]:
    """L'entrée du parcours : une seule source, contrôlée."""
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
        "Capture lancée : utilisateur %s, session %s, source %s",
        user_id,
        session_id,
        next(iter(payload)),
    )
    return CaptureStarted(session_id=session_id)
