"""Port de la capture rapide (`CaptureStore`, D108) sur la feature `capture` : implémentation
branchée par `bootstrap.agent_ports`. Chaque appel ouvre sa propre session de base, courte.

`store` range, en une transaction, l'élément de mémoire `document` (titre, résumé en cinq lignes,
« Source : {adresse} », étiquettes des modules), la ligne de journal `capture`
(« capture:{session} », qui le rend idempotent) et, pour une note « j'ai appris », les
compétences montées à `declare` au moins avec une preuve `capture` (F14 : `user_skills` fait
foi, jamais au-delà de ce qu'elles avaient). Après le commit : l'élément est indexé et les
niveaux reflétés dans la mémoire (idempotents, refaits au rejeu). `tick_task` prend le verrou
du programme AVANT sa transaction (F4). Journaux : identifiants et nombres seulement."""

import logging
from collections.abc import Sequence
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.capture_port import (
    CaptureDigest,
    CaptureMaterial,
    CaptureSource,
    CaptureStored,
    ProgramLinks,
)
from app.agents.tools.study_schema import CardDraft
from app.core.errors import AppError
from app.core.skills import evidence
from app.features.capture.service.journal import JournalLinks, add_entry, entry_by_ref
from app.features.capture.service.links import program_links
from app.features.capture.service.runtime import CaptureRuntime
from app.features.memory.service.captured import (
    CAPTURE_AUTHOR,
    document_state,
    index_capture,
    write_capture,
)
from app.features.memory.service.gateway import AgentMemoryGateway
from app.features.memory.service.skill_levels import reflect_skill_levels
from app.features.program.service.followup import program_of_task, tick_tasks
from app.features.quiz.service.cards import NewCard
from app.features.quiz.service.cards import add_cards as write_cards
from app.features.skills.service import SkillsService

logger = logging.getLogger(__name__)

MAX_CHUNKS = 40  # premiers fragments d'un document importé
MAX_TEXT_CHARS = 20_000
_SOURCE_LABEL = {"url": "Lien capturé", "document": "Document capturé", "text": "Note"}


def document_not_found() -> AppError:
    return AppError("document_not_found", "Document introuvable.", 404)


def document_failed() -> AppError:
    return AppError("document_failed", "Ce document n'a pas pu être importé.", 409)


def item_text(digest: CaptureDigest, material: CaptureMaterial) -> str:
    lines = "\n".join(f"- {line}" for line in digest.summary)
    return f"{lines}\n\nSource : {material.url}" if material.url else lines


def journal_text(source: CaptureSource, title: str) -> str:
    return f"{_SOURCE_LABEL[source]} : « {title} »"


def _learned(digest: CaptureDigest, source: CaptureSource) -> list[str]:
    """Les concepts « j'ai appris » d'une note de January (jamais d'une page ni d'un document)."""
    return list(digest.concepts) if digest.learned and source == "text" else []


def _ref(session_id: str) -> str:
    return f"capture:{session_id}"


class AgentCaptureStore:
    def __init__(self, runtime: CaptureRuntime) -> None:
        self._rt = runtime

    async def document(self, user_id: str, document_id: str) -> CaptureMaterial | None:
        async with self._rt.session_factory() as db:
            state = await document_state(db, user_id, document_id)
        if state is None:
            raise document_not_found()
        if state.status == "error":
            raise document_failed()
        if state.status != "indexed":
            return None
        gateway = AgentMemoryGateway(self._rt.memory)
        found = await gateway.document_text(user_id, document_id, max_chunks=MAX_CHUNKS)
        if found is None:
            return None
        text = "\n\n".join(found.chunks)[:MAX_TEXT_CHARS]
        return CaptureMaterial(found.title or state.name, text, state.url)

    async def links(self, user_id: str) -> ProgramLinks:
        async with self._rt.session_factory() as db:
            return await program_links(db, user_id, await self._rt.today(db, user_id))

    async def store(
        self,
        user_id: str,
        session_id: str,
        digest: CaptureDigest,
        material: CaptureMaterial,
        links: ProgramLinks,
        *,
        source: CaptureSource,
    ) -> CaptureStored:
        async with self._rt.session_factory() as db:
            entry = await entry_by_ref(db, user_id, _ref(session_id))
            if entry is not None and entry.memory_item_id:  # rejeu : déjà rangée
                written, entry_id, item_id = False, entry.id, entry.memory_item_id
            else:
                today = await self._rt.today(db, user_id)
                entry_id, item_id = await self._write(
                    db, user_id, session_id, digest, material, links, source, today
                )
                await db.commit()
                written = True
        await index_capture(self._rt.memory, user_id, item_id)
        if concepts := _learned(digest, source):
            await self._reflect(user_id, session_id, concepts, digest.title)
        if written:
            logger.info(
                "Capture rangée : utilisateur %s, session %s, élément %s, journal %s",
                user_id,
                session_id,
                item_id,
                entry_id,
            )
        covered = links.task(digest.covered_task) if digest.covered_task else None
        return CaptureStored(item_id, entry_id, covered)

    async def _write(
        self,
        db: AsyncSession,
        user_id: str,
        session_id: str,
        digest: CaptureDigest,
        material: CaptureMaterial,
        links: ProgramLinks,
        source: CaptureSource,
        today: date,
    ) -> tuple[str, str]:
        """Élément, journal et acquis dans la transaction de `db` (non commitée)."""
        modules = [m for ref in digest.modules if (m := links.module(ref)) is not None]
        item = await write_capture(
            db,
            self._rt.memory,
            user_id,
            title=digest.title,
            text=item_text(digest, material),
            tags=("capture", *(m.title for m in modules)),
            session_id=session_id,
        )
        concepts = _learned(digest, source)
        covered = links.task(digest.covered_task) if digest.covered_task else None
        entry_id = await add_entry(
            db,
            user_id,
            kind="capture",
            text=journal_text(source, digest.title),
            occurred_on=today,
            ref_key=_ref(session_id),
            links=JournalLinks(session_id=session_id, memory_item_id=item.id),
            data={
                "source": source,
                "module_ids": [m.module_id for m in modules],
                "concepts": concepts,
                "covered_task_id": covered.task_id if covered else None,
            },
        )
        if concepts:
            label = f"Capture « {digest.title} » ({today:%d/%m})"
            await SkillsService(db, user_id).raise_levels(
                concepts, "declare", evidence("capture", entry_id, label, self._rt.now())
            )
        return entry_id, item.id

    async def _reflect(
        self, user_id: str, session_id: str, concepts: list[str], title: str
    ) -> None:
        """Le niveau de chaque compétence (qui fait foi) reflété dans les acquis de la mémoire ;
        idempotent, jamais plus bas : refait au rejeu pour rattraper un arrêt."""
        try:
            async with self._rt.session_factory() as db:
                levels = await SkillsService(db, user_id).levels_of(concepts)
            await reflect_skill_levels(
                self._rt.memory,
                user_id,
                levels,
                author=CAPTURE_AUTHOR,
                session_id=session_id,
                reason=f"Capture « {title} » : January dit l'avoir appris.",
            )
        except Exception:
            logger.warning("Acquis non reflétés après une capture : session %s", session_id)

    async def tick_task(self, user_id: str, session_id: str, task_id: str) -> None:
        async with self._rt.session_factory() as db:
            program_id = await program_of_task(db, user_id, task_id)
        if program_id is None:
            logger.info("Capture : tâche inconnue ignorée (session %s)", session_id)
            return
        lock = self._rt.program.program_lock(user_id, program_id)
        async with lock, self._rt.session_factory() as db:  # le verrou AVANT la transaction (F4)
            await tick_tasks(db, self._rt.program, user_id, [task_id])
            await db.commit()

    async def add_cards(self, user_id: str, session_id: str, cards: Sequence[CardDraft]) -> int:
        async with self._rt.session_factory() as db:
            entry = await entry_by_ref(db, user_id, _ref(session_id))
            modules = [str(m) for m in (entry.data.get("module_ids", []) if entry else [])]
            module_id = modules[0] if modules else None
            source_id = entry.id if entry else None
            new = [
                NewCard(card.front, card.back, card.skill, module_id, "capture", source_id)
                for card in cards
            ]
            created = await write_cards(db, user_id, new, await self._rt.today(db, user_id))
            await db.commit()
        return created
