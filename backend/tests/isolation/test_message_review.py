from fastapi import FastAPI

from tests.isolation.conftest import Browser
from tests.mcp.adapter_support import call
from tests.mcp.support import API, Mcp
from tests.support.telegram_review import (
    CHAT,
    MOMENT,
    SETTINGS,
    add_card,
    configure,
    telegram_token,
)


async def test_telegram_settings_and_challenges_are_owned(
    google_client_factory: Browser, google_app: FastAPI
) -> None:
    owner = await google_client_factory("january@example.com")
    other = await google_client_factory("autre@example.com")
    nod = Mcp(owner)
    token = await telegram_token(owner)
    user_id = (await owner.get(f"{API}/auth/me")).json()["id"]
    await add_card(google_app, user_id)
    google_app.state.quiz.now = lambda: MOMENT
    _, blocked = await call(nod, token["token"], "message_review_claim", {"chat_id": CHAT})
    assert blocked
    assert (await configure(owner, token["id"])).status_code == 200
    _, wrong_chat = await call(nod, token["token"], "message_review_claim", {"chat_id": "123456"})
    assert wrong_chat
    challenge, blocked = await call(nod, token["token"], "message_review_claim", {"chat_id": CHAT})
    assert not blocked
    challenge_id = challenge["data"]["challenge"]["id"]

    settings = (await other.get(SETTINGS)).json()
    assert not settings["enabled"] and settings["chat_id"] is None and not settings["tokens"]
    assert (await configure(other, token["id"])).status_code == 404
    second = await telegram_token(other, label="Autre Nod")
    assert (await configure(other, second["id"])).status_code == 200
    body = {"chat_id": CHAT, "result": "ok"}
    direct = await other.post(f"{API}/message-reviews/{challenge_id}/answer", json=body)
    assert direct.status_code == 403
    _, wrong_owner = await call(
        Mcp(other), second["token"], "message_review_answer", {**body, "challenge_id": challenge_id}
    )
    assert wrong_owner

    assert (await owner.put(SETTINGS, json={"enabled": False})).status_code == 200
    _, revoked = await call(
        nod, token["token"], "message_review_answer", {**body, "challenge_id": challenge_id}
    )
    assert revoked and (await owner.get(f"{API}/flashcards/due")).json()["reviewed_today"] == 0
