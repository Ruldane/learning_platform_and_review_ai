"""Routes du kit de candidature (D143) : lancement (202, 409), les sept pièces dans l'ordre fixe,
la modification d'une pièce (recontrôlée par le code), les journaux sans donnée personnelle et
l'isolation entre utilisatrices."""

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import delete

from app.agents.tools.kit_schema import KIT_KINDS
from app.db.models.career import MasterProfile
from tests.features.applications.conftest import API
from tests.features.applications.kit_support import (
    COMPANY,
    CONTACT,
    TITLE,
    get_kit,
    item,
    kit_store,
    ready_application,
    save,
    spy,
)

ROOT = "/api/v1"

pytestmark = pytest.mark.usefixtures("client")


async def test_kit_launch_202_then_409(client: httpx.AsyncClient, app: FastAPI) -> None:
    launcher = spy(app)
    application_id = await ready_application(client, app)
    r = await client.post(f"{API}/{application_id}/kit")
    assert r.status_code == 202, r.text
    session_id = r.json()["session_id"]
    assert r.json() == {"session_id": session_id}
    assert launcher.started == [("application_kit", {"application_id": application_id})]
    view = (await client.get(f"{ROOT}/sessions/{session_id}")).json()
    assert (view["graph"], view["subject_type"], view["subject_id"]) == (
        "application_kit",
        "application_kit",
        application_id,
    )
    again = await client.post(f"{API}/{application_id}/kit")
    assert (again.status_code, again.json()["error"]["code"]) == (409, "kit_in_progress")
    assert again.json()["error"]["details"] == {"session_id": session_id}
    assert len(launcher.started) == 1
    # L'événement « lancé » entre au fil de la fiche, une seule fois.
    detail = (await client.get(f"{API}/{application_id}")).json()
    kits = [e for e in detail["events"] if e["kind"] == "kit"]
    assert [(e["text"], e["ref_id"]) for e in kits] == [("Application kit started.", session_id)]
    # Une fois la session finie, le kit se relance.
    assert (await client.post(f"{ROOT}/sessions/{session_id}/cancel")).status_code == 200
    second = await client.post(f"{API}/{application_id}/kit")
    assert second.status_code == 202 and second.json()["session_id"] != session_id


async def test_kit_launch_needs_a_posting_and_a_profile(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    launcher = spy(app)
    no_posting = await ready_application(client, app, posting_text=None)
    r = await client.post(f"{API}/{no_posting}/kit")
    assert (r.status_code, r.json()["error"]["code"]) == (409, "posting_required")
    # Le texte collé ensuite par `PATCH` (I1) ouvre le kit.
    patched = await client.patch(f"{API}/{no_posting}", json={"posting_text": "Texte collé."})
    assert patched.status_code == 200
    assert (await client.post(f"{API}/{no_posting}/kit")).status_code == 202
    no_profile = await ready_application(client, app, profile=False, title="Autre poste")
    # Le profil de la fiche précédente est validé : on le retire pour ce cas.
    async with app.state.session_factory() as db:
        await db.execute(delete(MasterProfile))
        await db.commit()
    r = await client.post(f"{API}/{no_profile}/kit")
    assert (r.status_code, r.json()["error"]["code"]) == (409, "profile_required")
    missing = await client.post(f"{API}/00000000-0000-4000-8000-000000000000/kit")
    assert (missing.status_code, missing.json()["error"]["code"]) == (404, "application_not_found")
    assert len(launcher.started) == 1  # le seul kit lancé : celui du texte collé


async def test_kit_launch_when_the_engine_is_down(client: httpx.AsyncClient, app: FastAPI) -> None:
    spy(app).refuse = True
    application_id = await ready_application(client, app)
    r = await client.post(f"{API}/{application_id}/kit")
    assert (r.status_code, r.json()["error"]["code"]) == (503, "engine_unavailable")
    detail = (await client.get(f"{API}/{application_id}")).json()
    assert [e for e in detail["events"] if e["kind"] == "kit"] == []  # rien n'a été lancé


async def test_get_kit_lists_seven_kinds(client: httpx.AsyncClient, app: FastAPI) -> None:
    spy(app)
    application_id = await ready_application(client, app)
    empty = await get_kit(client, application_id)
    assert (empty["session_id"], empty["running"]) == (None, False)
    assert [i["kind"] for i in empty["items"]] == list(KIT_KINDS)  # l'ordre fixe de F16
    assert {i["status"] for i in empty["items"]} == {"pending"}
    assert all(
        i["content"] == "" and i["id"] is None and i["updated_at"] is None for i in empty["items"]
    )

    session_id = (await client.post(f"{API}/{application_id}/kit")).json()["session_id"]
    piece_id = await save(
        app,
        application_id,
        "followups",
        session=session_id,
        content="Bonjour\n\n---\n\nRelance deux",
        meta={"words": {"day_7": 1, "day_14": 2}},
    )
    await save(
        app, application_id, "letter", session=session_id, status="to_check",
        content="Lettre", meta={"words": 1, "flags": ["5", "Kubernetes"]},
    )  # fmt: skip
    await save(
        app, application_id, "pitch", session=session_id, status="failed", content="",
        meta={"error": "Cette pièce a pris trop de temps", "code": "piece_timeout"},
    )  # fmt: skip
    kit = await get_kit(client, application_id)
    assert (kit["session_id"], kit["running"]) == (session_id, True)
    assert [i["kind"] for i in kit["items"]] == list(KIT_KINDS)
    followups, letter, pitch = (item(kit, k) for k in ("followups", "letter", "pitch"))
    assert (followups["id"], followups["status"], followups["words"]) == (piece_id, "ready", 3)
    assert (letter["status"], letter["flags"], letter["words"]) == (
        "to_check",
        ["5", "Kubernetes"],
        1,
    )
    assert (pitch["status"], pitch["error"], pitch["content"]) == (
        "failed",
        "Cette pièce a pris trop de temps",
        "",
    )
    assert item(kit, "cv")["status"] == "pending" and followups["edited"] is False
    assert followups["updated_at"] is not None
    await client.post(f"{ROOT}/sessions/{session_id}/cancel")
    after = await get_kit(client, application_id)
    assert (after["session_id"], after["running"]) == (session_id, False)  # la dernière session


async def test_form_answers_count_the_salary_fields_left_to_january(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    application_id = await ready_application(client, app)
    content = (
        "### Quelles sont vos prétentions salariales ?\nÀ remplir par toi\n\n"
        "### Avez-vous le permis B ?\nOui, je conduis régulièrement."
    )
    await save(app, application_id, "form_answers", status="to_check", content=content)
    form = item(await get_kit(client, application_id), "form_answers")
    assert (form["salary_fields"], form["status"]) == (1, "to_check")
    r = await client.patch(
        f"{API}/{application_id}/kit/form_answers",
        json={"content": content.replace("À remplir par toi", "45 k€")},
    )
    assert (r.json()["salary_fields"], r.json()["status"]) == (0, "ready")  # January l'a rempli


async def test_patch_marks_edited_and_rechecks(client: httpx.AsyncClient, app: FastAPI) -> None:
    application_id = await ready_application(client, app)
    await save(
        app, application_id, "letter", status="to_check", content="J'ai 5 ans sur Kubernetes.",
        meta={"language": "fr", "words": 6, "flags": ["5", "Kubernetes"]},
    )  # fmt: skip
    url = f"{API}/{application_id}/kit/letter"
    # Un terme que le profil ne dit toujours pas : à vérifier, les termes mis à jour.
    r = await client.patch(url, json={"content": "J'ai utilisé Kubernetes avec soin."})
    assert r.status_code == 200, r.text
    body = r.json()
    assert (body["status"], body["flags"], body["edited"]) == ("to_check", ["Kubernetes"], True)
    assert body["words"] == 5 and body["content"] == "J'ai utilisé Kubernetes avec soin."
    # Plus rien que le profil ne dise pas : prête.
    r = await client.patch(url, json={"content": "Je construis des solutions fiables avec soin."})
    body = r.json()
    assert (body["status"], body["flags"], body["edited"]) == ("ready", [], True)
    # La relecture du kit montre la même chose, et `updated_at` a bougé.
    kit_item = item(await get_kit(client, application_id), "letter")
    assert (kit_item["status"], kit_item["edited"], kit_item["flags"]) == ("ready", True, [])
    # Une pièce prête reste prête : la modification de January n'est pas relue.
    r = await client.patch(url, json={"content": "Elle sait Kubernetes et 12 outils."})
    assert (r.json()["status"], r.json()["edited"]) == ("ready", True)


async def test_patch_rechecks_each_part_and_never_the_questions(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    application_id = await ready_application(client, app)
    for kind in ("linkedin", "form_answers"):
        await save(app, application_id, kind, status="to_check", content="x")
    r = await client.patch(
        f"{API}/{application_id}/kit/linkedin",
        json={"content": "Bonjour, ravie d'échanger.\n---\nJ'ai piloté 12 projets."},
    )
    assert (r.json()["status"], r.json()["flags"]) == ("to_check", ["12"])
    # Les termes d'une question de l'offre (Kubernetes) ne sont pas ceux de January.
    form = "### Maîtrisez-vous Kubernetes ?\nJe construis des solutions fiables."
    r = await client.patch(f"{API}/{application_id}/kit/form_answers", json={"content": form})
    assert (r.json()["status"], r.json()["flags"]) == ("ready", [])
    blank = "### Disponibilité ?\nÀ compléter"
    r = await client.patch(f"{API}/{application_id}/kit/form_answers", json={"content": blank})
    assert (r.json()["status"], r.json()["edited"]) == ("ready", True)  # déjà prête : pas relue


async def test_patch_company_name_and_title_are_allowed_phrases(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    application_id = await ready_application(client, app)
    await save(app, application_id, "pitch", status="to_check", content="x")
    text = f"Je candidate à votre poste de {TITLE} chez {COMPANY} ; échangeons avec {CONTACT}."
    r = await client.patch(f"{API}/{application_id}/kit/pitch", json={"content": text})
    assert (r.json()["status"], r.json()["flags"]) == ("ready", [])


async def test_patch_empty_text_stays_to_check_and_failed_piece_can_be_filled(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    application_id = await ready_application(client, app)
    await save(app, application_id, "pitch", status="failed", meta={"error": "Trop long"})
    url = f"{API}/{application_id}/kit/pitch"
    r = await client.patch(url, json={"content": ""})
    assert (r.json()["status"], r.json()["error"]) == ("to_check", None)
    r = await client.patch(url, json={"content": "Je construis des solutions fiables."})
    assert (r.json()["status"], r.json()["error"]) == ("ready", None)


async def test_patch_errors_never_echo_the_text(client: httpx.AsyncClient, app: FastAPI) -> None:
    application_id = await ready_application(client, app)
    await save(app, application_id, "letter")
    url = f"{API}/{application_id}/kit/letter"
    too_long = await client.patch(url, json={"content": "z" * 20_001})
    assert too_long.status_code == 422
    assert too_long.json()["error"]["details"] == {"fields": ["content"]}
    assert "zzzzzzzz" not in too_long.text
    missing = await client.patch(url, json={})
    assert missing.status_code == 422 and missing.json()["error"]["details"] == {
        "fields": ["content"]
    }
    bad_kind = await client.patch(f"{API}/{application_id}/kit/inconnue", json={"content": "x"})
    assert bad_kind.status_code == 422 and "inconnue" not in bad_kind.text
    never_saved = await client.patch(f"{API}/{application_id}/kit/pitch", json={"content": "x"})
    assert (never_saved.status_code, never_saved.json()["error"]["code"]) == (
        404,
        "kit_item_not_found",
    )
    unknown = await client.patch(f"{API}/inconnue/kit/letter", json={"content": "x"})
    assert (unknown.status_code, unknown.json()["error"]["code"]) == (404, "application_not_found")
    ok = await client.patch(url, json={"content": "z" * 20_000})
    assert ok.status_code == 200


async def test_relaunch_keeps_edited(client: httpx.AsyncClient, app: FastAPI, me: str) -> None:
    spy(app)
    application_id = await ready_application(client, app)
    for kind in KIT_KINDS:
        await save(app, application_id, kind)
    await client.patch(f"{API}/{application_id}/kit/pitch", json={"content": "Mon pitch à moi."})
    await client.patch(f"{API}/{application_id}/kit/letter", json={"content": "Ma lettre."})
    ctx = await kit_store(app).context(me, application_id)
    assert ctx.keep == ["letter", "pitch"]  # dans l'ordre fixe : le parcours ne les refait pas
    r = await client.post(f"{API}/{application_id}/kit")
    assert r.status_code == 202
    session_id = r.json()["session_id"]
    for kind in KIT_KINDS:  # le parcours range ce qu'il refait ; les pièces gardées ne bougent pas
        await save(app, application_id, kind, session=session_id, content=f"Refait {kind}")
    kit = await get_kit(client, application_id)
    assert (item(kit, "pitch")["content"], item(kit, "pitch")["edited"]) == (
        "Mon pitch à moi.",
        True,
    )
    assert item(kit, "letter")["content"] == "Ma lettre."
    assert item(kit, "linkedin")["content"] == "Refait linkedin"
    assert item(kit, "linkedin")["edited"] is False
