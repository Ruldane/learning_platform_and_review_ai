"""API des leçons et des ressources (D91) : liste d'un programme, leçon et ses ressources, PDF et
copie locale servis à leur seul propriétaire, Bibliothèque filtrable, statut de lecture."""

from dataclasses import dataclass

import httpx
from fastapi import FastAPI

from app.db.models.lessons import Lesson, Resource
from app.features.program.service.programs import load
from app.features.program.service.store import AgentProgramStore
from app.features.research.service.cache import url_key
from tests.features.program.support import MONDAY, add_goal, sample_plan
from tests.sessions_support import act_as

API = "/api/v1"
PDF = b"%PDF-1.7 lecon %%EOF"


@dataclass(frozen=True)
class Seeded:
    program_id: str
    lesson_id: str
    pending_id: str
    resources: list[str]  # ids : article fr (copie locale), vidéo en, article en (lue)


def _resource(user_id: str, module_id: str, program_id: str, n: int, **extra: object) -> Resource:
    url = f"https://site{n}.exemple.org/page"
    fields: dict[str, object] = {
        "user_id": user_id,
        "module_id": module_id,
        "program_id": program_id,
        "type": "article",
        "title": f"Ressource {n}",
        "url": url,
        "url_hash": url_key(url),
        "author": "Autrice",
        "published": "2025-03-01",
        "lang": "fr",
        "duration_minutes": 15,
        "level": "debutant",
        "reason": "Bonne introduction.",
        "score": 75,
    }
    return Resource(**(fields | extra))


async def seed(app: FastAPI) -> Seeded:
    """Un brouillon (sans validation : aucune session réelle lancée), une leçon prête avec son
    PDF et trois ressources, une leçon en attente."""
    user_id: str = app.state.local_user_id
    factory = app.state.session_factory
    rows = await add_goal(factory, user_id)
    saved = await AgentProgramStore(app.state.program).save_draft(
        user_id, "s-draft", rows.goal_id, sample_plan(), revision=0, start_date=MONDAY, reason="v1"
    )
    pid = saved.program_id
    storage = app.state.lessons.storage
    pdf_key = await storage.save(user_id, "lessons", PDF, ".pdf")
    copy_key = await storage.save(user_id, "resources", PDF, ".pdf")
    async with factory() as db:
        first, second = [m.id for m in (await load(db, user_id, pid)).modules]
        ready = Lesson(
            user_id=user_id,
            module_id=first,
            program_id=pid,
            title="Module Bases",
            markdown="# Module Bases\n\nTexte.",
            word_count=1500,
            status="ready",
            pdf_key=pdf_key,
        )
        waiting = Lesson(user_id=user_id, module_id=second, program_id=pid, title="Module Projet")
        resources = [
            _resource(user_id, first, pid, 0, local_key=copy_key),
            _resource(user_id, first, pid, 1, type="video", lang="en", note="Fiche de lecture."),
            _resource(user_id, first, pid, 2, lang="en", status="read"),
        ]
        db.add_all([ready, waiting, *resources])
        await db.commit()
    return Seeded(pid, ready.id, waiting.id, [r.id for r in resources])


async def test_lesson_routes_and_isolation(client: httpx.AsyncClient, app: FastAPI) -> None:
    s = await seed(app)
    listed = (await client.get(f"{API}/programs/{s.program_id}/lessons")).json()
    assert [(x["id"], x["week_rank"], x["status"], x["pdf_available"]) for x in listed] == [
        (s.lesson_id, 1, "ready", True),
        (s.pending_id, 2, "pending", False),
    ]
    lesson = (await client.get(f"{API}/lessons/{s.lesson_id}")).json()
    assert lesson["markdown"].startswith("# Module Bases") and lesson["word_count"] == 1500
    assert [r["id"] for r in lesson["resources"]] == s.resources
    assert lesson["resources"][0]["has_local_copy"] is True
    assert lesson["resources"][1]["note"] == "Fiche de lecture."
    pdf = await client.get(f"{API}/lessons/{s.lesson_id}/pdf")
    assert pdf.status_code == 200 and pdf.content == PDF
    assert pdf.headers["content-type"] == "application/pdf"
    copy = await client.get(f"{API}/resources/{s.resources[0]}/file")
    assert copy.status_code == 200 and copy.content == PDF

    act_as(app, "un-autre-utilisateur")
    for path, code in [
        (f"/programs/{s.program_id}/lessons", "program_not_found"),
        (f"/lessons/{s.lesson_id}", "lesson_not_found"),
        (f"/lessons/{s.lesson_id}/pdf", "lesson_not_found"),
        (f"/resources/{s.resources[0]}/file", "resource_not_found"),
    ]:
        r = await client.get(f"{API}{path}")
        assert (r.status_code, r.json()["error"]["code"]) == (404, code), path
    assert (await client.get(f"{API}/resources")).json() == []
    r = await client.patch(f"{API}/resources/{s.resources[0]}", json={"status": "read"})
    assert r.status_code == 404


async def test_lesson_pdf_missing_is_404(client: httpx.AsyncClient, app: FastAPI) -> None:
    s = await seed(app)
    r = await client.get(f"{API}/lessons/{s.pending_id}/pdf")
    assert (r.status_code, r.json()["error"]["code"]) == (404, "lesson_pdf_missing")
    r = await client.get(f"{API}/resources/{s.resources[1]}/file")
    assert (r.status_code, r.json()["error"]["code"]) == (404, "resource_file_missing")


async def test_resources_filters(client: httpx.AsyncClient, app: FastAPI) -> None:
    s = await seed(app)

    async def ids(**params: str) -> set[str]:
        r = await client.get(f"{API}/resources", params=params)
        assert r.status_code == 200, r.text
        return {x["id"] for x in r.json()}

    every = set(s.resources)
    assert await ids() == every
    assert await ids(program_id=s.program_id) == every
    assert await ids(program_id="programme-inconnu") == set()
    assert await ids(type="video") == {s.resources[1]}
    assert await ids(lang="en") == {s.resources[1], s.resources[2]}
    assert await ids(status="read") == {s.resources[2]}
    assert await ids(type="article", lang="en", status="read") == {s.resources[2]}
    r = await client.get(f"{API}/resources", params={"type": "<script>inconnu</script>"})
    assert r.status_code == 422 and "<script>" not in r.text


async def test_resource_status_patch(client: httpx.AsyncClient, app: FastAPI) -> None:
    s = await seed(app)
    r = await client.patch(f"{API}/resources/{s.resources[0]}", json={"status": "read"})
    assert r.status_code == 200 and r.json()["status"] == "read"
    listed = (await client.get(f"{API}/resources", params={"status": "read"})).json()
    assert {x["id"] for x in listed} == {s.resources[0], s.resources[2]}
    r = await client.patch(f"{API}/resources/{s.resources[0]}", json={"status": "fini!secret"})
    assert r.status_code == 422 and "secret" not in r.text
