"""Port réel de la capture (`AgentCaptureStore`, D108) : élément `document` résumé et ligne de
journal idempotents par session, acquis `declare` d'une note « j'ai appris » (F14 : `user_skills`
fait foi, reflet dans la mémoire), liens vers le programme validé (F7), tâche cochée sous le
verrou du programme, fiches dédoublonnées, document importé attendu jusqu'à son indexation."""

from typing import Any

import pytest
from sqlalchemy import select

from app.agents.tools.capture_port import CaptureDigest, CaptureMaterial, ProgramLinks
from app.agents.tools.study_schema import CardDraft
from app.core.errors import AppError
from app.core.skills import normalize_skill_name
from app.db.models.memory import Document, MemoryChunk, MemoryItem
from app.db.models.program import Task
from app.db.models.skills import Skill, UserSkill
from app.db.models.study import Flashcard, JournalEntry
from app.features.program.service.programs import load
from app.features.skills.service import SkillsService
from tests.features.capture.conftest import Capture
from tests.features.program.support import Factory
from tests.features.replan.conftest import ME, OTHER, drafted, validated
from tests.support.capture import SUMMARY

URL = "https://blog.exemple.org/attention"
PAGE = CaptureMaterial("Comprendre l'attention", "Le texte de la page.", URL)


def _digest(**over: Any) -> CaptureDigest:
    data: dict[str, Any] = {
        "title": "Les DataFrames pandas",
        "summary": SUMMARY,
        "concepts": ["pandas", "Docker"],
        "modules": ["m1"],
        "covered_task": "t1",
    }
    return CaptureDigest.model_validate(data | over)


async def _rows[T](factory: Factory, model: type[T], user_id: str = ME) -> list[T]:
    async with factory() as db:
        stmt = select(model).where(model.user_id == user_id)  # type: ignore[attr-defined]
        return list((await db.execute(stmt)).scalars().all())


async def _levels(factory: Factory) -> dict[str, tuple[str, list[Any]]]:
    async with factory() as db:
        skills = {s.id: s.norm_name for s in (await db.execute(select(Skill))).scalars()}
        rows = (await db.execute(select(UserSkill).where(UserSkill.user_id == ME))).scalars()
        return {skills[r.skill_id]: (r.level, list(r.evidence)) for r in rows}


async def test_links_list_validated_modules_and_tasks_within_a_week(capture: Capture) -> None:
    program_id = await validated(capture.program, ME)
    await drafted(capture.program, ME)  # un brouillon n'est pas relié
    links = await capture.store.links(ME)
    assert [(m.ref, m.title) for m in links.modules] == [
        ("m1", "Module Bases"),
        ("m2", "Module Projet"),
    ]
    async with capture.rt.session_factory() as db:
        loaded = await load(db, ME, program_id)
    near = [t for t in loaded.tasks if t.planned_date.isoformat() <= "2026-11-25"]
    assert [t.task_id for t in links.tasks] == [
        t.id for t in sorted(near, key=lambda t: (t.planned_date, loaded.tasks.index(t)))
    ]
    assert links.tasks[0].ref == "t1" and links.tasks[0].late  # lundi 16 : avant mercredi 18
    assert (await capture.store.links(OTHER)) == ProgramLinks([], [])


async def test_store_writes_summarized_document_and_journal_once(capture: Capture) -> None:
    await validated(capture.program, ME)
    links = await capture.store.links(ME)
    stored = await capture.store.store(ME, "s-1", _digest(), PAGE, links, source="url")
    again = await capture.store.store(ME, "s-1", _digest(), PAGE, links, source="url")
    assert again == stored and stored.covered_task == links.task("t1")
    factory = capture.rt.session_factory
    [item] = [i for i in await _rows(factory, MemoryItem) if i.kind == "document"]
    assert item.id == stored.memory_item_id and item.created_by == "archivist"
    assert item.title == "Les DataFrames pandas" and item.indexed_at is not None
    assert item.text == "\n".join(f"- {line}" for line in SUMMARY) + f"\n\nSource : {URL}"
    assert item.tags == ["capture", "Module Bases"] and item.source_id is None
    assert item.meta["reason"] == "Capture rapide de January." and item.session_id == "s-1"
    [entry] = await _rows(factory, JournalEntry)
    assert entry.id == stored.journal_entry_id and entry.kind == "capture"
    assert entry.ref_key == "capture:s-1" and entry.memory_item_id == item.id
    assert entry.text == "Lien capturé : « Les DataFrames pandas »"
    assert entry.occurred_on.isoformat() == "2026-11-18" and entry.session_id == "s-1"
    assert "Docker" not in str(await _levels(factory))  # une page ne déclare rien


async def test_learned_note_writes_declare_acquis(capture: Capture) -> None:
    await validated(capture.program, ME)
    factory = capture.rt.session_factory
    async with factory() as db:  # pandas déjà en cours : jamais baissé
        await SkillsService(db, ME).raise_levels(
            ["pandas"], "en_cours", {"kind": "study", "ref_id": "x", "label": "S", "at": ""}
        )
        await db.commit()
    note = CaptureMaterial("", "J'ai appris pandas et Docker.", None)
    digest = _digest(learned=True, covered_task=None)
    links = await capture.store.links(ME)
    stored = await capture.store.store(ME, "s-2", digest, note, links, source="text")
    await capture.store.store(ME, "s-2", digest, note, links, source="text")  # rejeu
    levels = await _levels(factory)
    assert levels["pandas"][0] == "en_cours" and levels["docker"][0] == "declare"
    proofs = [p for p in levels["docker"][1] if p["kind"] == "capture"]
    assert [p["ref_id"] for p in proofs] == [stored.journal_entry_id]  # une preuve, F14
    assert proofs[0]["label"] == "Capture « Les DataFrames pandas » (18/11)"
    acquis = {
        normalize_skill_name(i.title): i.meta["level"]
        for i in await _rows(factory, MemoryItem)
        if i.kind == "acquis"
    }
    assert acquis["docker"] == "declare" and acquis["pandas"] == "en_cours"  # reflet (D6)
    [item] = [i for i in await _rows(factory, MemoryItem) if i.kind == "document"]
    assert "Source" not in item.text
    [entry] = await _rows(factory, JournalEntry)
    assert entry.text == "Note : « Les DataFrames pandas »"


async def test_tick_task_under_program_lock_and_cards_once(capture: Capture) -> None:
    await validated(capture.program, ME)
    theirs = await validated(capture.program, OTHER)
    links = await capture.store.links(ME)
    await capture.store.store(ME, "s-3", _digest(), PAGE, links, source="url")
    task = links.tasks[0]
    await capture.store.tick_task(ME, "s-3", task.task_id)
    await capture.store.tick_task(ME, "s-3", task.task_id)  # idempotent
    other_task = (await _rows(capture.rt.session_factory, Task, OTHER))[0]
    await capture.store.tick_task(ME, "s-3", other_task.id)  # la tâche d'une autre : ignorée
    statuses = {t.id: t.status for t in await _rows(capture.rt.session_factory, Task)}
    assert statuses[task.task_id] == "done"
    assert all(t.status == "todo" for t in await _rows(capture.rt.session_factory, Task, OTHER))
    assert theirs
    cards = [
        CardDraft(front="Qu'est-ce qu'un DataFrame ?", back="Un tableau.", skill="pandas"),
        CardDraft(front="Qu'est-ce qu'une Series ?", back="Une colonne."),
    ]
    assert await capture.store.add_cards(ME, "s-3", cards) == 2
    assert await capture.store.add_cards(ME, "s-3", cards) == 0  # dédoublonnées par recto
    rows = await _rows(capture.rt.session_factory, Flashcard)
    [entry] = await _rows(capture.rt.session_factory, JournalEntry)
    assert {(c.source, c.source_id, c.module_id) for c in rows} == {
        ("capture", entry.id, links.modules[0].module_id)
    }
    assert {c.due_date.isoformat() for c in rows} == {"2026-11-19"}  # demain chez January


async def _document(factory: Factory, user_id: str, status: str) -> str:
    async with factory() as db:
        item = MemoryItem(
            user_id=user_id, kind="document", title="Notes de cours", text="Texte complet.",
            created_by="user", content_hash=f"hash-{user_id}-{status}",
        )  # fmt: skip
        db.add(item)
        await db.flush()
        db.add(MemoryChunk(user_id=user_id, item_id=item.id, ordinal=0, text="Partie 1.",
                           token_count=2))  # fmt: skip
        db.add(MemoryChunk(user_id=user_id, item_id=item.id, ordinal=1, text="Partie 2.",
                           token_count=2))  # fmt: skip
        doc = Document(
            user_id=user_id, name="notes.pdf", source_kind="pdf", status=status,
            source_hash=f"src-{user_id}-{status}", item_id=item.id,
        )  # fmt: skip
        db.add(doc)
        await db.commit()
        return doc.id


async def test_document_material_waits_for_indexing(capture: Capture) -> None:
    factory = capture.rt.session_factory
    queued = await _document(factory, ME, "processing")
    assert await capture.store.document(ME, queued) is None
    ready = await _document(factory, ME, "indexed")
    found = await capture.store.document(ME, ready)
    assert found == CaptureMaterial("Notes de cours", "Partie 1.\n\nPartie 2.", None)
    failed = await _document(factory, ME, "error")
    with pytest.raises(AppError) as error:
        await capture.store.document(ME, failed)
    assert error.value.code == "document_failed"
    theirs = await _document(factory, OTHER, "indexed")
    with pytest.raises(AppError) as missing:
        await capture.store.document(ME, theirs)
    assert (missing.value.code, missing.value.status_code) == ("document_not_found", 404)
