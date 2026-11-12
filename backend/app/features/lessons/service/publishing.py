"""Suites de la publication d'une leçon (D91), chacune idempotente et sans transaction ouverte
pendant le réseau (D66) : copies locales des PDF libres des ressources (sinon fiche de lecture),
PDF A4 de la leçon (Gotenberg), leçon rangée dans la mémoire (`lecon`). Une panne de l'une est
journalisée par son type et n'empêche ni les autres ni la publication : la leçon se lit dans
l'application et le rejeu du nœud (ou la prochaine publication) rattrape ce qui manque."""

import logging
from dataclasses import dataclass

from app.agents.tools.memory_port import AgentWrite
from app.features.lessons.repository import LessonRepository, ResourceRepository
from app.features.lessons.service.render import render_lesson_pdf
from app.features.lessons.service.runtime import LessonsRuntime
from app.features.memory.service.gateway import AgentMemoryGateway
from app.features.research.service.download import download_pdf
from app.features.research.service.reading import list_sources

logger = logging.getLogger(__name__)

AUTHOR = "writer"
NOTE_MAX = 2000


@dataclass(frozen=True)
class Published:
    """Ce que les suites relisent de la leçon publiée."""

    user_id: str
    session_id: str
    lesson_id: str
    module_id: str
    title: str
    markdown: str
    language: str
    program_title: str


async def _pending_copies(rt: LessonsRuntime, p: Published) -> list[tuple[str, str, str | None]]:
    """`(ressource, adresse, source)` des ressources dont la copie n'a pas encore été tentée."""
    async with rt.session_factory() as db:
        rows = await ResourceRepository(db, p.user_id).for_module(p.module_id)
    return [(r.id, r.url, r.source_id) for r in rows if r.local_key is None and r.note is None]


async def _notes(rt: LessonsRuntime, p: Published) -> dict[str, str]:
    """Fiche de lecture de chaque source de la session : son résumé, à défaut sa raison."""
    async with rt.session_factory() as db:
        sources = await list_sources(db, p.user_id, p.session_id)
    return {s.id: ((s.summary or s.reason or "").strip()[:NOTE_MAX]) for s in sources}


async def copy_resources(rt: LessonsRuntime, p: Published) -> None:
    """PDF librement téléchargeable → copie locale (catégorie `resources`), sinon fiche de
    lecture. Une ressource tranchée (copie ou fiche) ne se retente pas au rejeu."""
    pending = await _pending_copies(rt, p)
    if not pending:
        return
    notes = await _notes(rt, p)
    copied = 0
    for resource_id, url, source_id in pending:
        data = await download_pdf(rt.research, p.user_id, url)
        key = None if data is None else await rt.storage.save(p.user_id, "resources", data, ".pdf")
        async with rt.session_factory() as db:
            row = await ResourceRepository(db, p.user_id).get(resource_id)
            if row is not None and row.local_key is None:
                row.local_key = key
                row.note = None if key else (notes.get(source_id or "") or "Fiche indisponible.")
            await db.commit()
        copied += key is not None
    logger.info(
        "Ressources : leçon %s, %d copie(s) locale(s) sur %d", p.lesson_id, copied, len(pending)
    )


async def lesson_pdf(rt: LessonsRuntime, p: Published) -> bool:
    """PDF A4 de la leçon (catégorie `lessons`), une seule fois ; `False` s'il manque encore."""
    async with rt.session_factory() as db:
        lesson = await LessonRepository(db, p.user_id).get_fresh(p.lesson_id)
        if lesson is None or lesson.pdf_key is not None:
            return lesson is not None
    try:
        pdf = await render_lesson_pdf(
            rt.publishing.html_pdf, title=p.title, markdown=p.markdown, language=p.language
        )
        key = await rt.storage.save(p.user_id, "lessons", pdf, ".pdf")
    except Exception as exc:
        logger.warning("PDF de la leçon %s non produit (%s)", p.lesson_id, type(exc).__name__)
        return False
    async with rt.session_factory() as db:
        lesson = await LessonRepository(db, p.user_id).get_fresh(p.lesson_id)
        kept = lesson is not None and lesson.pdf_key is None
        if lesson is not None and kept:
            lesson.pdf_key = key
        await db.commit()
    if not kept:  # rangé entre-temps par un autre appel (ou leçon disparue) : le nôtre est en trop
        await rt.storage.delete(p.user_id, key)
    return lesson is not None


async def remember(rt: LessonsRuntime, p: Published) -> None:
    """La leçon dans la mémoire (`lecon` : titre, Markdown, étiquette du programme) ; le même
    contenu rejoué n'écrit rien de plus (dédoublonnage de la mémoire)."""
    write = AgentWrite(
        kind="lecon",
        title=p.title,
        text=p.markdown,
        reason="Leçon du programme publiée après contrôle du Vérificateur.",
        tags=(p.program_title,),
    )
    try:
        await AgentMemoryGateway(rt.memory).write(p.user_id, p.session_id, AUTHOR, write)
    except Exception as exc:
        logger.warning("Leçon %s non rangée en mémoire (%s)", p.lesson_id, type(exc).__name__)


async def finish(rt: LessonsRuntime, p: Published) -> bool:
    """Les trois suites ; rend « le PDF de la leçon est prêt »."""
    try:
        await copy_resources(rt, p)
    except Exception as exc:
        logger.warning("Ressources de la leçon %s (%s)", p.lesson_id, type(exc).__name__)
    pdf_ok = await lesson_pdf(rt, p)
    await remember(rt, p)
    return pdf_ok
