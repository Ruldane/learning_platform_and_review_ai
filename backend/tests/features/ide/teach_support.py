"""Matériel des tests du professeur (10.A3) : faux modèles scriptés qui gardent chaque appel
(niveau, agent, messages), réponses JSON du professeur, et états posés en base. Aucun appel réel
au modèle."""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

import httpx
from fastapi import FastAPI
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage

from app.db.base import utcnow
from app.db.models.agents import AgentSession, LlmCall
from app.db.models.ide import IdeNote, IdePreference, IdeRun
from app.features.ide.service import error_signature
from app.providers.llm.base import Tier
from app.providers.llm.fake import FakeChatModel, _Script
from tests.features.ide.support import API, TRACE, USER
from tests.sessions_support import wait_status

MAIN = "\n".join(f"line_{n} = {n}" for n in range(1, 121)) + "\n"
SIGNATURE = error_signature(TRACE, {"main.py"})


@dataclass
class Call:
    tier: Tier
    agent: str
    messages: list[BaseMessage]


@dataclass
class ScriptedModels:
    """`ChatModelSource` de test : rend les `replies` dans l'ordre, note chaque appel. `hold`
    fige les appels jusqu'à son déclenchement."""

    replies: list[str] = field(default_factory=list)
    calls: list[Call] = field(default_factory=list)
    hold: asyncio.Event | None = None
    received: list[list[BaseMessage]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._script = _Script(self.replies, self.received)

    async def get_chat_model(
        self, user_id: str, tier: Tier, agent: str | None = None
    ) -> BaseChatModel:
        self.calls.append(Call(tier, agent or "", []))
        meta = {"tremplin_provider": "fake", "tremplin_model": f"modele-{tier}"}
        return _HeldChat(script=self._script, metadata=meta, hold=self.hold)


class _HeldChat(FakeChatModel):
    hold: Any = None

    async def _astream(self, *args: Any, **kwargs: Any) -> Any:
        if self.hold is not None:
            await self.hold.wait()
        async for chunk in super()._astream(*args, **kwargs):
            yield chunk


def note_json(kind: str = "hint", text: str = "Regarde la ligne 3.", **over: Any) -> str:
    return json.dumps({"kind": kind, "text": text, **over})


async def wait_done(client: httpx.AsyncClient, session_id: str) -> dict[str, Any]:
    return await wait_status(client, session_id, "completed")


async def teach(
    client: httpx.AsyncClient, session_id: str, trigger: str = "hint", **body: Any
) -> httpx.Response:
    return await client.post(
        f"{API}/sessions/{session_id}/teach", json={"trigger": trigger, **body}
    )


async def add_failed_run(app: FastAPI, session_id: str, signature: str | None = SIGNATURE) -> str:
    """Une exécution en erreur, figée, avec sa signature."""
    async with app.state.session_factory() as db:
        run = IdeRun(
            user_id=USER,
            session_id=session_id,
            kind="run",
            entry="main.py",
            status="done",
            exit_code=1,
            output=TRACE,
            error_signature=signature,
        )
        db.add(run)
        await db.commit()
        return run.id


async def add_professor_note(
    app: FastAPI, session_id: str, error_key: str | None, kind: str = "hint", age_s: int = 0
) -> str:
    async with app.state.session_factory() as db:
        note = IdeNote(
            user_id=USER,
            session_id=session_id,
            kind=kind,
            author="professor",
            content="Regarde la ligne 3.",
            error_key=error_key,
            created_at=utcnow() - timedelta(seconds=age_s),
        )
        db.add(note)
        await db.commit()
        return note.id


async def add_teacher_tokens(
    app: FastAPI, ide_session_id: str | None, tokens: int, *, age_days: int = 0
) -> None:
    """Des jetons du professeur déjà consommés : une session d'agents `ide_teacher` (sujet : la
    séance de code) et son appel journalisé."""
    async with app.state.session_factory() as db:
        agent_session = AgentSession(
            user_id=USER,
            graph="ide_teacher",
            status="completed",
            subject_type="ide_session",
            subject_id=ide_session_id,
        )
        db.add(agent_session)
        await db.flush()
        db.add(
            LlmCall(
                user_id=USER,
                session_id=agent_session.id,
                graph="ide_teacher",
                agent="professor",
                provider="fake",
                model="modele-rapide",
                tokens_in=tokens - tokens // 10,
                tokens_out=tokens // 10,
                created_at=utcnow() - timedelta(days=age_days),
            )
        )
        await db.commit()


async def set_preferences(app: FastAPI, **fields: Any) -> None:
    async with app.state.session_factory() as db:
        db.add(IdePreference(user_id=USER, **fields))
        await db.commit()
