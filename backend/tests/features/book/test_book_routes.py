from io import BytesIO
from zipfile import ZipFile

import httpx
from fastapi import FastAPI

from app.db.models.brain import BrainFile, BrainFolder
from app.db.models.lessons import Lesson
from app.db.models.memory import Document, MemoryItem
from app.features.book.service.refresh import refresh_book, refresh_books
from app.features.program.service.programs import load
from tests.features.program.conftest import Draft
from tests.sessions_support import act_as
from tests.support.memory import FakeHtmlRenderer


def path(draft: Draft) -> str:
    return f"/api/v1/programs/{draft.program_id}/book"


async def publish(app: FastAPI, draft: Draft, index: int, text: str) -> str:
    async with app.state.session_factory() as db:
        program = await load(db, draft.user_id, draft.program_id)
        lesson = Lesson(
            user_id=draft.user_id,
            program_id=draft.program_id,
            module_id=program.modules[index].id,
            title=f"Leçon {index + 1}",
            markdown=f"## Explication\n\n{text}\n",
            status="ready",
        )
        db.add(lesson)
        await db.commit()
        return lesson.id


async def test_queue_then_refresh_on_publication(
    client: httpx.AsyncClient,
    app: FastAPI,
    draft_program: Draft,
    fake_html_renderer: FakeHtmlRenderer,
) -> None:
    path_ = path(draft_program)
    await publish(app, draft_program, 0, "Premier chapitre")
    opened = await client.get(path_)
    assert opened.json()["status"] == "not_requested"
    queued = await client.post(path_)
    assert queued.status_code == 202 and queued.json()["status"] == "queued"
    assert fake_html_renderer.documents == []
    assert (await client.get(f"{path_}/epub")).status_code == 404

    await refresh_books(app.state.book)
    pdf = await client.get(f"{path_}/pdf")
    epub = await client.get(f"{path_}/epub")
    assert pdf.headers["content-type"] == "application/pdf" and pdf.content.startswith(b"%PDF")
    assert epub.headers["content-type"] == "application/epub+zip"
    assert epub.headers["cache-control"] == "private, no-store"
    assert epub.headers["content-disposition"] == 'attachment; filename="ton-livre.epub"'
    state = (await client.get(path_)).json()
    assert (state["status"], state["chapters"], state["available"]) == ("ready", 1, True)

    await publish(app, draft_program, 1, "Deuxième chapitre")
    await refresh_book(app.state.book, draft_program.user_id, draft_program.program_id)
    updated = await client.get(f"{path_}/epub")
    with ZipFile(BytesIO(updated.content)) as archive:
        assert "Deuxième chapitre".encode() in archive.read("EPUB/chapter-2.xhtml")
    await refresh_book(app.state.book, draft_program.user_id, draft_program.program_id)
    assert len(fake_html_renderer.documents) == 2


async def test_book_routes_are_isolated(
    client: httpx.AsyncClient, app: FastAPI, draft_program: Draft
) -> None:
    path_ = path(draft_program)
    assert (await client.post(path_)).status_code == 202
    await refresh_book(app.state.book, draft_program.user_id, draft_program.program_id)
    act_as(app, "autre-compte")
    try:
        for suffix in ("", "/pdf", "/epub"):
            assert (await client.get(f"{path_}{suffix}")).status_code == 404
        assert (await client.post(path_)).status_code == 404
    finally:
        app.dependency_overrides.clear()


async def test_failed_redraw_preserves_previous_pair(
    client: httpx.AsyncClient,
    app: FastAPI,
    draft_program: Draft,
    fake_html_renderer: FakeHtmlRenderer,
) -> None:
    path_ = path(draft_program)
    await publish(app, draft_program, 0, "Premier chapitre")
    await client.post(path_)
    await refresh_book(app.state.book, draft_program.user_id, draft_program.program_id)
    pdf = (await client.get(f"{path_}/pdf")).content
    epub = (await client.get(f"{path_}/epub")).content
    await publish(app, draft_program, 1, "Deuxième chapitre")
    fake_html_renderer.failures = 1
    await refresh_book(app.state.book, draft_program.user_id, draft_program.program_id)
    state = (await client.get(path_)).json()
    assert state["status"] == "failed" and state["available"] is True
    assert (await client.get(f"{path_}/pdf")).content == pdf
    assert (await client.get(f"{path_}/epub")).content == epub


async def add_note(app: FastAPI, user_id: str, lesson_id: str) -> str:
    async with app.state.session_factory() as db:
        folder = BrainFolder(user_id=user_id, name="Notes", path="recette")
        item = MemoryItem(
            user_id=user_id,
            kind="document",
            title="Note liée",
            text="Un rappel d’Obsidian.",
            created_by="user",
            content_hash="rappel",
        )
        db.add_all([folder, item])
        await db.flush()
        document = Document(
            user_id=user_id,
            name="note.md",
            source_kind="markdown",
            status="indexed",
            source_hash="note",
            item_id=item.id,
            sync_metadata={"links": [f"tremplin:lesson:{lesson_id}"]},
        )
        db.add(document)
        await db.flush()
        file = BrainFile(
            user_id=user_id,
            folder_id=folder.id,
            document_id=document.id,
            path="note.md",
            sha256="note",
            size=21,
        )
        db.add(file)
        await db.commit()
        return file.id


async def test_removed_note_disappears_from_the_next_edition(
    client: httpx.AsyncClient, app: FastAPI, draft_program: Draft
) -> None:
    owner = draft_program.user_id
    program = draft_program.program_id
    lesson = await publish(app, draft_program, 0, "Premier chapitre")
    note = await add_note(app, owner, lesson)
    await add_note(app, "autre-compte", lesson)
    path_ = path(draft_program)
    await client.post(path_)
    await refresh_book(app.state.book, owner, program)
    with ZipFile(BytesIO((await client.get(f"{path_}/epub")).content)) as epub:
        text = epub.read("EPUB/chapter-1.xhtml").decode()
        assert text.count("Un rappel d’Obsidian.") == 1

    async with app.state.session_factory() as db:
        file = await db.get(BrainFile, note)
        assert file is not None
        await db.delete(file)
        await db.commit()

    await refresh_book(app.state.book, owner, program)
    with ZipFile(BytesIO((await client.get(f"{path_}/epub")).content)) as epub:
        assert "Un rappel d’Obsidian." not in epub.read("EPUB/chapter-1.xhtml").decode()
