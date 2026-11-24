"""API du profil maître (D124) : versions validées par January (jamais d'écrasement, ids gardés,
conflit de version), compétences déclarées sans baisse et reflétées dans les acquis (D6), 422
sans valeur, import du CV et de LinkedIn comme documents de la mémoire puis capture lancée, refus
des fichiers qui ne sont pas des PDF, une capture à la fois, rien du profil dans les journaux."""

import logging
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select

from app.agents.tools.cv_schema import MasterProfileData
from app.core.skills import evidence
from app.db.models.memory import Document, MemoryItem
from app.features.skills.service import SkillsService
from scripts.sample_cv import CV_FACTS, SampleCv, make_cv_pdf
from tests.features.cv.conftest import API, skill_rows
from tests.features.lessons.conftest import RecordingLauncher
from tests.support.profile import NOTE, profile_data

SECRET_ROLE = "Rôle secret à ne jamais recopier"


async def put(client: httpx.AsyncClient, data: dict[str, Any], base: int | None) -> httpx.Response:
    return await client.put(f"{API}/profile", json={"data": data, "base_version": base})


def pdf_files(linkedin: bool = True) -> dict[str, tuple[str, bytes, str]]:
    files = {"cv": ("CV_Camille_Exemple.pdf", make_cv_pdf(), "application/pdf")}
    if linkedin:
        files["linkedin"] = ("Profile.pdf", make_cv_pdf(SampleCv(columns=1)), "application/pdf")
    return files


async def test_put_profile_creates_validated_version_and_raises_skills(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    r = await put(client, profile_data(), None)
    assert r.status_code == 200, r.text
    body = r.json()
    assert (body["version"], body["status"], body["source"]) == (1, "validated", "january")
    assert [x["id"] for x in body["data"]["experiences"]] == ["x1", "x2"]
    assert body["data"]["experiences"][0]["sources"] == ["note"]  # sources envoyées gardées
    assert body["data"]["education"][0]["sources"] == ["january"]  # aucune : January
    levels = await skill_rows(app.state.session_factory, app.state.local_user_id)
    assert {name: level for name, (level, _) in levels.items()} == {
        name: "declare" for name in CV_FACTS["tools"].split(", ")
    }
    [proof] = levels["Python"][1]
    assert (proof["kind"], proof["label"]) == ("cv", "Profil maître") and proof["ref_id"]
    async with app.state.session_factory() as db:  # reflet dans les acquis de la mémoire (D6)
        acquis = (await db.execute(select(MemoryItem).where(MemoryItem.kind == "acquis"))).scalars()
        reflected = {item.title: item.meta["level"] for item in acquis}
    assert reflected == {name: "declare" for name in CV_FACTS["tools"].split(", ")}
    state = (await client.get(f"{API}/profile")).json()
    assert state["validated"]["version"] == 1 and state["draft"] is None
    assert state["session_id"] is None
    versions = (await client.get(f"{API}/profile/versions")).json()
    assert [(v["version"], v["status"], v["source"]) for v in versions] == [
        (1, "validated", "january")
    ]


async def test_put_profile_never_lowers_a_skill(client: httpx.AsyncClient, app: FastAPI) -> None:
    user = app.state.local_user_id
    async with app.state.session_factory() as db:
        quiz = evidence("quiz", "q1", "Quiz", app.state.career.cv.now())
        await SkillsService(db, user).raise_levels(["Python"], "valide", quiz)
        await db.commit()
    assert (await put(client, profile_data(), None)).status_code == 200
    levels = await skill_rows(app.state.session_factory, user)
    assert levels["Python"][0] == "valide" and levels["Docker"][0] == "declare"
    async with app.state.session_factory() as db:  # l'acquis suit le niveau qui fait foi
        python = (
            await db.execute(
                select(MemoryItem).where(MemoryItem.kind == "acquis", MemoryItem.title == "Python")
            )
        ).scalar_one()
    assert python.meta["level"] == "valide"
    assert [p["kind"] for p in levels["Python"][1]] == ["quiz", "cv"]


async def test_put_profile_conflict_and_ids_kept(client: httpx.AsyncClient) -> None:
    first = (await put(client, profile_data(), None)).json()
    stale = await put(client, profile_data(), None)
    assert stale.status_code == 409 and stale.json()["error"]["code"] == "profile_conflict"
    assert stale.json()["error"]["message"] == "Your profile has changed. Reload it before saving."
    edited = first["data"]
    edited["experiences"][0]["role"] = "Ingénieure IA"
    edited["skills"].append({"id": "", "name": "Qdrant"})
    second = await put(client, edited, 1)
    assert second.status_code == 200 and second.json()["version"] == 2
    data = second.json()["data"]
    job = data["experiences"][0]
    assert job["id"] == "x1" and job["role"] == "Ingénieure IA"
    assert data["skills"][-1]["id"] == "c6"
    assert (await put(client, edited, 1)).status_code == 409


async def test_put_profile_422_has_paths_not_values(client: httpx.AsyncClient) -> None:
    data = profile_data()
    data["experiences"].append({"role": SECRET_ROLE * 10, "company": ""})
    data["identity"]["email"] = "x" * 300
    r = await put(client, data, None)
    assert r.status_code == 422
    error = r.json()["error"]
    assert error["code"] == "validation_error"
    assert set(error["details"]["fields"]) == {
        "experiences.2.role",
        "experiences.2.company",
        "identity.email",
    }
    assert SECRET_ROLE not in r.text and "xxxxxxxx" not in r.text


async def test_draft_is_shown_only_when_newer(client: httpx.AsyncClient, app: FastAPI) -> None:
    store, user = app.state.career.profile, app.state.local_user_id
    launcher = RecordingLauncher(app.state.session_factory)
    sid = await launcher.start(user, "cv_capture", {"mode": "profile", "document_ids": ["d"]})
    draft = (await client.get(f"{API}/profile")).json()
    assert draft == {
        "validated": None,
        "draft": None,
        "session_id": None,
        "source_document_id": None,
    }
    await store.save_draft(user, sid, MasterProfileData.model_validate(profile_data()), ["x"])
    state = (await client.get(f"{API}/profile")).json()
    assert state["draft"]["version"] == 1 and state["draft"]["dropped"] == ["x"]
    assert state["draft"]["source"] == "archivist" and state["validated"] is None
    assert (await put(client, state["draft"]["data"], 1)).status_code == 200
    state = (await client.get(f"{API}/profile")).json()
    assert state["draft"] is None and state["validated"]["version"] == 2


async def test_import_launches_capture(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher
) -> None:
    r = await client.post(f"{API}/profile/import", files=pdf_files(), data={"note": NOTE})
    assert r.status_code == 202, r.text
    body = r.json()
    assert len(body["document_ids"]) == 2
    [(graph, given)] = launcher_spy.started
    assert graph == "cv_capture"
    assert given == {"mode": "profile", "document_ids": body["document_ids"], "note": NOTE}
    async with app.state.session_factory() as db:
        docs = {d.id: d for d in (await db.execute(select(Document))).scalars()}
    cv_id, linkedin_id = body["document_ids"]
    assert docs[cv_id].tags == ["cv"] and docs[linkedin_id].tags == ["linkedin"]
    assert docs[cv_id].source_kind == "pdf"
    state = (await client.get(f"{API}/profile")).json()
    assert state["session_id"] == body["session_id"]
    await app.state.memory.jobs.join()  # éléments `document` étiquetés à l'ingestion
    async with app.state.session_factory() as db:
        items = {i.source_id: i for i in (await db.execute(select(MemoryItem))).scalars()}
    assert items[cv_id].tags == ["cv"] and items[linkedin_id].tags == ["linkedin"]


async def test_state_exposes_the_imported_cv_document(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher
) -> None:
    """`source_document_id` : le CV (étiqueté `cv`) du dernier import, jamais LinkedIn ; `None`
    tant qu'aucun brouillon n'en garde la trace."""
    assert (await client.get(f"{API}/profile")).json()["source_document_id"] is None
    r = await client.post(f"{API}/profile/import", files=pdf_files(), data={"note": NOTE})
    cv_id, linkedin_id = r.json()["document_ids"]
    assert (await client.get(f"{API}/profile")).json()["source_document_id"] is None
    draft = MasterProfileData.model_validate(profile_data())
    await app.state.career.profile.save_draft(
        app.state.local_user_id, r.json()["session_id"], draft, []
    )
    state = (await client.get(f"{API}/profile")).json()
    assert state["source_document_id"] == cv_id != linkedin_id
    assert (await put(client, state["draft"]["data"], 1)).status_code == 200  # version validée
    assert (await client.get(f"{API}/profile")).json()["source_document_id"] == cv_id
    async with app.state.session_factory() as db:  # document retiré de la mémoire
        await db.delete(await db.get(Document, cv_id))
        await db.commit()
    assert (await client.get(f"{API}/profile")).json()["source_document_id"] is None


async def test_import_rejects_non_pdf(
    client: httpx.AsyncClient, launcher_spy: RecordingLauncher
) -> None:
    for name, data in [("cv.pdf", b"pas un PDF"), ("cv.docx", make_cv_pdf())]:
        files = {"cv": (name, data, "application/octet-stream")}
        r = await client.post(f"{API}/profile/import", files=files)
        assert r.status_code == 415
        error = r.json()["error"]
        assert error["code"] == "unsupported_file_type"
        assert error["message"] == "Upload a PDF file."
    big = {"cv": ("cv.pdf", b"%PDF-" + b"0" * (10 * 1024 * 1024), "application/pdf")}
    r = await client.post(f"{API}/profile/import", files=big)
    assert r.status_code == 413
    assert r.json()["error"]["message"] == "The file exceeds the 10 MB limit."
    missing = await client.post(f"{API}/profile/import", data={"note": NOTE})
    assert missing.status_code == 422 and missing.json()["error"]["details"]["fields"] == ["cv"]
    assert launcher_spy.started == []


async def test_import_twice_is_409(
    client: httpx.AsyncClient, launcher_spy: RecordingLauncher, app: FastAPI
) -> None:
    first = await client.post(f"{API}/profile/import", files=pdf_files(linkedin=False))
    assert first.status_code == 202
    again = await client.post(f"{API}/profile/import", files=pdf_files(linkedin=False))
    assert again.status_code == 409
    error = again.json()["error"]
    assert error["code"] == "capture_in_progress"
    assert error["details"] == {"session_id": first.json()["session_id"]}
    await launcher_spy.end(app.state.local_user_id, first.json()["session_id"], "failed")
    third = await client.post(f"{API}/profile/import", files=pdf_files(linkedin=False))
    assert third.status_code == 202
    assert third.json()["document_ids"] == first.json()["document_ids"]  # même document


async def test_profile_never_logged(
    client: httpx.AsyncClient, launcher_spy: RecordingLauncher, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)
    caplog.set_level(logging.DEBUG, logger="app")
    assert (await put(client, profile_data(), None)).status_code == 200
    r = await client.post(f"{API}/profile/import", files=pdf_files(), data={"note": NOTE})
    assert r.status_code == 202
    await client.get(f"{API}/profile")
    bad = profile_data()
    bad["experiences"][0]["start"] = SECRET_ROLE
    assert (await put(client, bad, 1)).status_code == 422
    for secret in (
        CV_FACTS["name"],
        CV_FACTS["email"],
        CV_FACTS["phone"],
        CV_FACTS["role_1"],
        SECRET_ROLE,
        NOTE,
        "CV_Camille",
    ):
        assert secret not in caplog.text
