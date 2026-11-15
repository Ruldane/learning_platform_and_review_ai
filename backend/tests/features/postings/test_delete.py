"""Suppression d'une offre (revue finale BR-I1, BC-I1) : 409 tant qu'une revue de CV est lancée ou
proposée, ou que l'analyse de l'offre est ouverte ; sinon les lignes (revues, modifications,
versions) partent, la transaction est validée, PUIS les PDF et les images des versions sont
effacés du stockage."""

import asyncio

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import func, select

from app.db.models.career import CvModification, CvReview, CvVersion
from tests.features.lessons.conftest import RecordingLauncher
from tests.features.postings.conftest import API
from tests.features.postings.test_router import _analyze, _create

CATEGORY = "cv_versions"


async def _review(app: FastAPI, posting_id: str, status: str) -> str:
    async with app.state.session_factory() as db:
        review = CvReview(
            user_id=app.state.local_user_id, posting_id=posting_id, template_id="t",
            profile_version=1, status=status,
        )  # fmt: skip
        db.add(review)
        await db.commit()
        return review.id


async def _count(app: FastAPI, model: type) -> int:
    async with app.state.session_factory() as db:
        return int((await db.execute(select(func.count()).select_from(model))).scalar_one())


async def _ready(app: FastAPI, launcher: RecordingLauncher, created: dict[str, str]) -> None:
    """L'offre analysée, sa session d'analyse terminée : rien ne s'oppose plus à la suppression."""
    await _analyze(app, created)
    await launcher.end(app.state.local_user_id, created["session"])


@pytest.mark.parametrize("status", ["running", "proposed"])
async def test_delete_refused_while_a_review_is_open(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher, status: str
) -> None:
    created = await _create(client)
    await _ready(app, launcher_spy, created)
    await _review(app, created["id"], status)
    r = await client.delete(f"{API}/postings/{created['id']}")
    assert (r.status_code, r.json()["error"]["code"]) == (409, "review_in_progress")
    assert (await client.get(f"{API}/postings/{created['id']}")).status_code == 200


async def test_delete_allowed_once_the_review_is_closed(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher
) -> None:
    created = await _create(client)
    await _ready(app, launcher_spy, created)
    await _review(app, created["id"], "done")
    assert (await client.delete(f"{API}/postings/{created['id']}")).status_code == 204


async def test_delete_refused_while_the_analysis_is_open(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher
) -> None:
    created = await _create(client)  # sa session d'analyse tourne
    r = await client.delete(f"{API}/postings/{created['id']}")
    assert (r.status_code, r.json()["error"]["code"]) == (409, "analysis_in_progress")
    assert "réessaie" in r.json()["error"]["message"]
    await launcher_spy.end(app.state.local_user_id, created["session"], "failed")
    assert (await client.delete(f"{API}/postings/{created['id']}")).status_code == 204


async def test_delete_cascades_rows_then_erases_version_files(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher
) -> None:
    created = await _create(client)
    await _ready(app, launcher_spy, created)
    review_id = await _review(app, created["id"], "done")
    user = app.state.local_user_id
    storage = app.state.career.postings.memory.providers.storage
    pdf = await storage.save(user, CATEGORY, b"%PDF-1.4 cv", ".pdf")
    page = await storage.save(user, CATEGORY, b"png", ".png")
    keep = await storage.save(user, CATEGORY, b"autre offre", ".pdf")  # une autre offre
    async with app.state.session_factory() as db:
        db.add_all(
            [
                CvModification(
                    user_id=user, review_id=review_id, ref="m1", section="experience",
                    action="rewrite", before="a", after="b", reason="r", type="clarity",
                    status="proposed", author="recruiter",
                ),
                CvVersion(
                    user_id=user, review_id=review_id, posting_id=created["id"],
                    template_id="t", number=1, status="ready", content={}, filename="CV_x.pdf",
                    original_page_count=1, storage_key=pdf, page_images=[page],
                ),
            ]
        )  # fmt: skip
        await db.commit()
    assert (await client.delete(f"{API}/postings/{created['id']}")).status_code == 204
    for model in (CvReview, CvModification, CvVersion):
        assert await _count(app, model) == 0, model.__name__
    for key in (pdf, page):
        with pytest.raises(FileNotFoundError):
            await storage.read(user, key)
    assert await storage.read(user, keep) == b"autre offre"


async def test_files_stay_when_the_delete_is_refused(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher
) -> None:
    created = await _create(client)
    await _ready(app, launcher_spy, created)
    review_id = await _review(app, created["id"], "proposed")
    user = app.state.local_user_id
    storage = app.state.career.postings.memory.providers.storage
    pdf = await storage.save(user, CATEGORY, b"%PDF-1.4 cv", ".pdf")
    async with app.state.session_factory() as db:
        db.add(
            CvVersion(
                user_id=user, review_id=review_id, posting_id=created["id"], template_id="t",
                number=1, status="ready", content={}, filename="CV_x.pdf",
                original_page_count=1, storage_key=pdf, page_images=[],
            )
        )  # fmt: skip
        await db.commit()
    assert (await client.delete(f"{API}/postings/{created['id']}")).status_code == 409
    assert await storage.read(user, pdf) == b"%PDF-1.4 cv"


async def test_delete_races_with_review_creation(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher
) -> None:
    """Course m-6 : la suppression prend le verrou des revues de l'utilisatrice avant de vérifier.
    Une revue créée sous ce verrou pendant que la suppression attend est donc vue : 409, et rien
    n'est parti en cascade."""
    created = await _create(client)
    await _ready(app, launcher_spy, created)
    lock = app.state.career.cv.review_lock(app.state.local_user_id)
    async with lock:  # un lancement de revue est en cours
        deleting = asyncio.create_task(client.delete(f"{API}/postings/{created['id']}"))
        await asyncio.sleep(0.1)
        assert not deleting.done()  # la suppression attend le verrou
        await _review(app, created["id"], "running")  # la revue est créée avant son commit
    r = await deleting
    assert (r.status_code, r.json()["error"]["code"]) == (409, "review_in_progress")
    assert (await client.get(f"{API}/postings/{created['id']}")).status_code == 200
    assert await _count(app, CvReview) == 1
