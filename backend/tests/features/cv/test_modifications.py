"""Décisions sur les modifications d'une revue (D128, D130) : accepter et refuser, « à confirmer »
jamais accepté sans confirmation explicite ni en groupe, fait confirmé ajouté au profil maître
(nouvelle version validée), texte réécrit revalidé, mot clé de l'offre absent du profil refusé
sans écho."""

import httpx
from fastapi import FastAPI

from app.agents.tools.cv_schema import MasterProfileData
from app.db.models.career import MasterProfile
from app.features.cv.repository import ProfileRepository
from tests.features.cv.reviews_support import (
    API,
    EDITED,
    SECRET_LINE,
    decide,
    mods,
    open_review,
)
from tests.features.lessons.conftest import RecordingLauncher


async def latest_profile(app: FastAPI) -> MasterProfile:
    async with app.state.session_factory() as db:
        row = await ProfileRepository(db, app.state.local_user_id).latest()
    assert row is not None
    return row


async def test_patch_accept_and_refuse(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher
) -> None:
    review_id, _ = await open_review(client, app)
    by_ref = await mods(client, review_id)
    r = await decide(client, by_ref["a1"]["id"], "accepted")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "accepted"
    r = await decide(client, by_ref["a1"]["id"], "refused")
    assert r.json()["status"] == "refused"
    r = await decide(client, by_ref["r1"]["id"], "refused")  # un « à confirmer » se refuse
    assert r.json()["status"] == "refused" and r.json()["blocks"]
    assert (await decide(client, "inconnue", "accepted")).status_code == 404
    bad = await decide(client, by_ref["a1"]["id"], "maybe")
    assert bad.status_code == 422 and bad.json()["error"]["details"] == {"fields": ["status"]}


async def test_to_confirm_needs_explicit_confirm_and_adds_fact(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher
) -> None:
    review_id, _ = await open_review(client, app)
    mid = (await mods(client, review_id))["r1"]["id"]
    r = await decide(client, mid, "accepted")
    assert (r.status_code, r.json()["error"]["code"]) == (409, "confirmation_required")
    assert (await mods(client, review_id))["r1"]["status"] == "to_confirm"
    assert (await latest_profile(app)).version == 1
    r = await client.patch(
        f"{API}/cv/modifications/{mid}", json={"status": "accepted", "confirm": True}
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "accepted" and r.json()["blocks"] == []
    latest = await latest_profile(app)
    assert (latest.version, latest.status, latest.source) == (2, "validated", "january")
    data = MasterProfileData.model_validate(latest.data)
    experience = data.experiences[0]
    assert [line.text for line in experience.achievements if line.id == "x1a2"] == [SECRET_LINE]
    assert "january" in experience.sources
    # refusée puis reprise : le fait est déjà au profil, plus de confirmation demandée
    await decide(client, mid, "refused")
    assert (await decide(client, mid, "accepted")).json()["status"] == "accepted"


async def test_bulk_accept_skips_to_confirm(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher
) -> None:
    review_id, _ = await open_review(client, app)
    by_ref = await mods(client, review_id)
    all_ids = [m["id"] for m in by_ref.values()]
    to_confirm_id = by_ref["r1"]["id"]
    r = await client.patch(
        f"{API}/cv/reviews/{review_id}/modifications", json={"ids": all_ids, "status": "accepted"}
    )
    assert r.status_code == 200, r.text
    assert r.json() == {"updated": 3, "skipped": [to_confirm_id]}
    after = await mods(client, review_id)
    assert after["r1"]["status"] == "to_confirm"
    assert {after[ref]["status"] for ref in ("a1", "a2", "r2")} == {"accepted"}
    # refusée, elle garde ses raisons : jamais acceptée en groupe non plus
    await decide(client, to_confirm_id, "refused")
    again = await client.patch(
        f"{API}/cv/reviews/{review_id}/modifications",
        json={"ids": [to_confirm_id, "inconnue"], "status": "accepted"},
    )
    assert again.json() == {"updated": 0, "skipped": [to_confirm_id, "inconnue"]}
    refused = await client.patch(
        f"{API}/cv/reviews/{review_id}/modifications", json={"ids": all_ids, "status": "refused"}
    )
    assert refused.json() == {"updated": 4, "skipped": []}
    too_many = await client.patch(
        f"{API}/cv/reviews/{review_id}/modifications", json={"ids": ["x"] * 51, "status": "refused"}
    )
    assert too_many.status_code == 422


async def test_edited_text_is_revalidated(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher
) -> None:
    review_id, _ = await open_review(client, app)
    mid = (await mods(client, review_id))["a1"]["id"]
    invented = "Réduit les coûts de 45 % avec Python"
    r = await decide(client, mid, "accepted", after=invented)
    assert r.status_code == 200, r.text
    assert (r.json()["status"], r.json()["after"]) == ("to_confirm", invented)
    assert r.json()["blocks"] == ["Number missing from your profile"]
    r = await decide(client, mid, "accepted", after=EDITED)
    assert (r.json()["status"], r.json()["after"], r.json()["blocks"]) == ("accepted", EDITED, [])
    gap = "Réduit les coûts de 30 % avec Python et RAG"
    r = await decide(client, mid, "accepted", after=gap)
    assert (r.status_code, r.json()["error"]["code"]) == (422, "keyword_not_in_profile")
    assert r.json()["error"]["message"] == (
        "This edit contains a posting keyword missing from your profile. It stays in the skill gap."
    )
    assert "RAG" not in r.text and gap not in r.text
    assert (await mods(client, review_id))["a1"]["after"] == EDITED  # rien n'a changé
    remove_id = (await mods(client, review_id))["r2"]["id"]
    r = await decide(client, remove_id, "accepted", after="Un texte")
    assert r.status_code == 422 and r.json()["error"]["details"] == {"fields": ["after"]}
    long = await decide(client, mid, "accepted", after="x" * 601)
    assert long.status_code == 422 and "x" * 601 not in long.text


async def test_confirm_refused_while_a_profile_draft_is_pending(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher
) -> None:
    """Revue 6.14, I-1 : confirmer un fait passerait au-dessus du brouillon de l'Archiviste et le
    cacherait ; refusé (409), rien n'est écrit, puis possible une fois le brouillon validé."""
    review_id, _ = await open_review(client, app)
    mid = (await mods(client, review_id))["r1"]["id"]
    user = app.state.local_user_id
    session_id = await launcher_spy.start(
        user, "cv_capture", {"mode": "profile", "document_ids": ["d"]}
    )
    validated = await latest_profile(app)  # le profil de la revue, repris en brouillon v2
    draft = MasterProfileData.model_validate(validated.data)
    await app.state.career.profile.save_draft(user, session_id, draft, [])
    r = await decide(client, mid, "accepted", confirm=True)
    error = r.json()["error"]
    assert (r.status_code, error["code"]) == (409, "profile_draft_pending")
    assert error["message"] == ("Approve the pending profile draft before confirming this fact.")
    assert (await mods(client, review_id))["r1"]["status"] == "to_confirm"  # rien d'écrit
    assert (await latest_profile(app)).status == "draft"
    state = (await client.get(f"{API}/profile")).json()
    assert state["draft"]["version"] == 2 and state["validated"]["version"] == 1
    r = await client.put(f"{API}/profile", json={"data": state["draft"]["data"], "base_version": 2})
    assert r.status_code == 200 and r.json()["version"] == 3
    r = await decide(client, mid, "accepted", confirm=True)
    assert r.status_code == 200, r.text
    assert (await latest_profile(app)).version == 4


async def test_blank_after_is_422_without_echo(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher
) -> None:
    review_id, _ = await open_review(client, app)
    mid = (await mods(client, review_id))["a1"]["id"]
    before = (await mods(client, review_id))["a1"]["after"]
    for blank in ("   ", "\n\t "):
        r = await decide(client, mid, "accepted", after=blank)
        assert r.status_code == 422, r.text
        assert r.json()["error"]["details"] == {"fields": ["after"]}
        assert blank not in r.text
    assert (await mods(client, review_id))["a1"]["after"] == before
