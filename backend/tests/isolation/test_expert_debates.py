"""Isolation des prises de parole et du jugement."""

from uuid import uuid4

from fastapi import FastAPI

from app.agents.tools.expert_debate_port import EXPERT_GRAPH, EXPERT_SCOPE
from app.db.models.agents import AgentSession
from app.db.models.conversations import ConversationTurn
from app.features.conversations.service import ConversationThread, ensure_conversation
from tests.isolation.conftest import Browser

API = "/api/v1/expert-debates"


async def test_debate_is_private_to_the_question_author(
    google_app: FastAPI, google_client_factory: Browser
) -> None:
    author = await google_client_factory("debats-a@example.test")
    other = await google_client_factory("debats-b@example.test")
    user_id = (await author.get("/api/v1/auth/me")).json()["id"]
    debate = str(uuid4())
    thread = ConversationThread.for_subject(user_id, EXPERT_SCOPE, debate, graph=EXPERT_GRAPH)
    async with google_app.state.session_factory() as db:
        await ensure_conversation(db, user_id, thread)
        session = AgentSession(user_id=user_id, graph=EXPERT_GRAPH, status="completed", input={})
        db.add(session)
        await db.flush()
        db.add(
            ConversationTurn(
                user_id=user_id,
                thread_id=thread.id,
                request_id=debate,
                session_id=session.id,
                question="Une question privée fictive",
                strong=False,
                answer="Débat terminé.",
                expert_speeches=[
                    {"role": "researcher", "text": "Réponse fictive.", "citations": []}
                ],
            )
        )
        await db.commit()
    route = f"{API}/{debate}"
    assert (await other.get(API)).json() == []
    assert (await other.get(route)).status_code == 404
    assert (await other.put(f"{route}/judgment", json={"text": "Texte tiers"})).status_code == 404
    assert (await author.put(f"{route}/judgment", json={"text": "Mon jugement"})).status_code == 200
    assert (await author.get(route)).json()["judgment"] == "Mon jugement"
