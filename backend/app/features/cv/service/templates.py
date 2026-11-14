"""Gabarits de CV côté API (SPEC 5.2, 14.2 ; D126) : liste, détail, images des pages, gabarit
actif, archivage ; la création est dans `templates_create`.

Le statut suit l'issue de la session : un gabarit `capturing` dont la session n'est plus ouverte
(panne du modèle, plafond, délai, annulation, arrêt) passe en `failed` à la lecture suivante,
sous le verrou des gabarits (une session terminée ne reprend jamais : la correction est sûre).
Journaux : identifiants et nombres, jamais le nom du gabarit, un fichier ni une police."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models.career import CvTemplate
from app.features.cv.repository import TemplateRepository
from app.features.cv.schemas_templates import (
    FontUseOut,
    TemplateOut,
    TemplateSummaryOut,
    ZoneDiffOut,
)
from app.features.cv.service.runtime import CAPTURE_GRAPH, TEMPLATE_SUBJECT, CvRuntime
from app.features.cv.service.templates_data import (
    template_not_found,
)
from app.features.sessions.service import list_open_sessions_by_subject

logger = logging.getLogger(__name__)

INTERRUPTED = "La capture du modèle s'est arrêtée avant la fin : relance-la."


def capture_in_progress(session_id: str) -> AppError:
    return AppError(
        "capture_in_progress",
        "Une capture de modèle de CV est déjà en cours.",
        409,
        {"session_id": session_id},
    )


def template_not_ready() -> AppError:
    return AppError(
        "template_not_ready", "Ce modèle n'est pas prêt : termine d'abord sa capture.", 409
    )


def template_in_use() -> AppError:
    return AppError(
        "template_in_use", "Une revue en cours emploie ce modèle : termine-la d'abord.", 409
    )


def page_not_found() -> AppError:
    return AppError("template_page_not_found", "Page du modèle introuvable.", 404)


async def _open_captures(db: AsyncSession, user_id: str) -> dict[str, list[str]]:
    return await list_open_sessions_by_subject(
        db, user_id, graph=CAPTURE_GRAPH, subject_type=TEMPLATE_SUBJECT
    )


async def settle(db: AsyncSession, user_id: str) -> dict[str, list[str]]:
    """Gabarits en capture sans session ouverte → `failed` ; rend les sessions ouvertes.
    Sessions lues AVANT les gabarits (D97 n° 9). L'appelant tient `template_lock`."""
    open_ids = await _open_captures(db, user_id)
    stale = [
        row
        for row in await TemplateRepository(db, user_id).capturing()
        if row.session_id is None or row.session_id not in open_ids.get(row.id, [])
    ]
    for row in stale:
        row.status, row.failure_reason = "failed", INTERRUPTED
        logger.info("Gabarit sans session : utilisateur %s, gabarit %s", user_id, row.id)
    if stale:
        await db.commit()
    return open_ids


def to_summary(row: CvTemplate) -> TemplateSummaryOut:
    return TemplateSummaryOut.model_validate(_summary_fields(row))


def _summary_fields(row: CvTemplate) -> dict[str, object]:
    return {
        "id": row.id,
        "name": row.name,
        "status": row.status,
        "active": row.active,
        "score": row.score,
        "passes": row.passes,
        "page_count": row.page_count,
        "created_at": row.created_at,
    }


def to_out(row: CvTemplate) -> TemplateOut:
    zones = (row.score_detail or {}).get("zones", [])
    return TemplateOut.model_validate(
        {
            **_summary_fields(row),
            "selectable": row.selectable,
            "fonts": [FontUseOut.model_validate(use) for use in row.fonts],
            "font_gaps": [str(gap) for gap in row.font_gaps],
            "zones": [ZoneDiffOut.model_validate(zone) for zone in zones],
            "session_id": row.session_id,
            "failure_reason": row.failure_reason,
        }
    )


async def _visible(db: AsyncSession, user_id: str, template_id: str) -> CvTemplate:
    row = await TemplateRepository(db, user_id).get(template_id)
    if row is None or row.status == "archived":
        raise template_not_found()
    return row


async def list_templates(rt: CvRuntime, user_id: str) -> list[TemplateSummaryOut]:
    async with rt.template_lock(user_id), rt.session_factory() as db:
        await settle(db, user_id)
        return [to_summary(row) for row in await TemplateRepository(db, user_id).visible()]


async def get_template(rt: CvRuntime, user_id: str, template_id: str) -> TemplateOut:
    async with rt.template_lock(user_id), rt.session_factory() as db:
        await settle(db, user_id)
        return to_out(await _visible(db, user_id, template_id))


async def page_png(rt: CvRuntime, user_id: str, template_id: str, kind: str, number: int) -> bytes:
    """Image d'une page (`number` depuis 1) de l'original ou du rendu de la passe courante ;
    404 pour une autre sorte (`PageKind`) ou un autre numéro."""
    if kind not in ("original", "render"):
        raise page_not_found()
    async with rt.session_factory() as db:
        row = await _visible(db, user_id, template_id)
    keys = row.original_pages if kind == "original" else row.render_pages
    if not 1 <= number <= len(keys):
        raise page_not_found()
    return await rt.storage.read(user_id, str(keys[number - 1]))


async def activate_template(rt: CvRuntime, user_id: str, template_id: str) -> None:
    async with rt.template_lock(user_id), rt.session_factory() as db:
        await settle(db, user_id)
        row = await _visible(db, user_id, template_id)
        if row.status != "ready":
            raise template_not_ready()
        current = await TemplateRepository(db, user_id).active()
        if current is not None and current.id != row.id:
            current.active = False
            await db.flush()  # un seul actif : l'index unique partiel est vérifié ligne à ligne
        row.active = True
        await db.commit()
    logger.info("Gabarit actif : utilisateur %s, gabarit %s", user_id, template_id)


async def archive_template(rt: CvRuntime, user_id: str, template_id: str) -> None:
    """Statut `archived` (images, polices et document gardés) ; idempotent."""
    async with rt.template_lock(user_id), rt.session_factory() as db:
        open_ids = await settle(db, user_id)
        row = await TemplateRepository(db, user_id).get(template_id)
        if row is None:
            raise template_not_found()
        if row.status == "archived":
            return
        if row.status == "capturing" and open_ids.get(row.id):
            raise capture_in_progress(open_ids[row.id][0])
        if await TemplateRepository(db, user_id).in_review(template_id):
            raise template_in_use()
        row.status, row.active = "archived", False
        await db.commit()
    logger.info("Gabarit archivé : utilisateur %s, gabarit %s", user_id, template_id)
