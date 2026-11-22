from hashlib import sha256
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select

from app.db.models.brain import BrainFile, BrainFolder
from app.db.models.memory import Document, MemoryChunk, MemoryItem
from app.providers.llm.fake import FakeLlmProvider
from tests.sessions_support import wait_status
from tests.support.conversation_lessons import add_ready_lesson

BRAIN_CHAT = "/api/v1/brain/conversation"
_OLD = "Constante obsolète quasar-orphelin."


async def add_note(app: FastAPI, user_id: str, title: str, text: str) -> tuple[str, str]:
    async with app.state.session_factory() as db:
        folder = BrainFolder(user_id=user_id, name=title, path=f"C:/notes/{uuid4()}")
        item = MemoryItem(
            user_id=user_id,
            kind="document",
            title=title,
            text=text,
            content_hash=sha256(text.encode()).hexdigest(),
            created_by="user",
        )
        db.add_all([folder, item])
        await db.flush()
        document = Document(
            user_id=user_id,
            name=title,
            source_kind="markdown",
            status="indexed",
            item_id=item.id,
            source_hash=sha256(uuid4().bytes).hexdigest(),
        )
        db.add(document)
        await db.flush()
        file = BrainFile(
            user_id=user_id,
            folder_id=folder.id,
            document_id=document.id,
            path="note.md",
            sha256=sha256(text.encode()).hexdigest(),
            size=len(text),
        )
        db.add_all(
            [
                file,
                MemoryChunk(user_id=user_id, item_id=item.id, ordinal=0, text=text, token_count=10),
            ]
        )
        await db.commit()
        return item.id, file.id


async def talk(client: httpx.AsyncClient, question: str) -> str:
    sent = await client.post(
        f"{BRAIN_CHAT}/messages", json={"request_id": str(uuid4()), "question": question}
    )
    assert sent.status_code == 202, sent.text
    sid: str = sent.json()["session_id"]
    await wait_status(client, sid, "completed")
    return sid


@pytest.mark.usefixtures("brain_citations")
async def test_brain_cites_only_current_synced_notes_and_followed_courses(
    client: httpx.AsyncClient,
    app: FastAPI,
) -> None:
    assert (await client.get(BRAIN_CHAT)).json() is None
    owner = app.state.local_user_id
    note_id, _ = await add_note(app, owner, "Astronomie", "Astronomie stellaire et référentiel.")
    await add_note(app, "compte-tiers", "Astronomie", "Contenu confidentiel d’un autre compte.")
    active = await add_ready_lesson(app, owner, "Astronomie suivie")
    await add_ready_lesson(app, owner, "Astronomie en brouillon", validated=False)
    await talk(client, "Astronomie")
    thread = (await client.get(BRAIN_CHAT)).json()
    (turn,) = thread["turns"]
    assert {s["id"] for s in turn["sources"]} == {note_id, active}


@pytest.mark.parametrize("action", ["remove", "replace"])
async def test_old_note_is_excluded_from_model_history_but_stays_readable(
    brain_history: FakeLlmProvider,
    client: httpx.AsyncClient,
    app: FastAPI,
    action: str,
) -> None:
    owner = app.state.local_user_id
    old_item, file_id = await add_note(app, owner, "Astronomie", f"Astronomie. {_OLD}")
    await talk(client, "Astronomie")
    await talk(client, "Résume, s'il te plaît.")
    assert _OLD in " ".join(str(msg.content) for msg in brain_history.received[1])
    async with app.state.session_factory() as db:
        file = await db.get(BrainFile, file_id)
        assert file is not None
        if action == "remove":
            await db.delete(file)
        else:
            item = await db.get(MemoryItem, old_item)
            assert item is not None
            item.text = "Astronomie. La note a été révisée."
            item.content_hash = sha256(item.text.encode()).hexdigest()
            chunk = await db.scalar(select(MemoryChunk).where(MemoryChunk.item_id == old_item))
            assert chunk is not None
            chunk.text = item.text
        await db.commit()
    await talk(client, "Astronomie")
    assert _OLD not in " ".join(str(msg.content) for msg in brain_history.received[2])
    turns = (await client.get(BRAIN_CHAT)).json()["turns"]
    assert all(_OLD in turn["answer"] for turn in turns[:2])
