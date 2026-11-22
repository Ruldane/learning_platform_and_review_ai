from fastapi import FastAPI

from tests.isolation.conftest import Browser
from tests.mcp.adapter_support import call
from tests.mcp.support import API, Mcp
from tests.support.surprise_interview import SETTINGS, configure_pair, invitation
from tests.support.telegram_review import CHAT
from tests.support.telegram_review import SETTINGS as REVIEW_SETTINGS


async def test_invitation_and_consent_are_private(
    google_app: FastAPI, google_client_factory: Browser
) -> None:
    owner = await google_client_factory("surprise-a@example.test")
    other = await google_client_factory("surprise-b@example.test")
    token = await configure_pair(owner)
    invite = await invitation(owner, google_app, token)
    config = (await other.get(SETTINGS)).json()
    assert not config["enabled"] and not config["tokens"] and not config["telegram_ready"]
    second = await configure_pair(other)
    args = {"chat_id": CHAT, "invitation_id": invite}
    envelope, failed = await call(Mcp(other), second, "surprise_interview_state", args)
    assert failed and envelope["data"]["error"]["code"] == "surprise_invitation_not_found"
    raw = await owner.post(f"{API}/surprise-interviews/{invite}/accept", json={"chat_id": CHAT})
    assert raw.status_code == 403
    _, wrong_chat = await call(
        Mcp(owner), token, "surprise_interview_accept", {**args, "chat_id": "505060"}
    )
    assert wrong_chat
    assert (await owner.put(REVIEW_SETTINGS, json={"enabled": False})).status_code == 200
    _, disconnected = await call(Mcp(owner), token, "surprise_interview_state", args)
    assert disconnected
