"""Routeur `cv` (paquet : profil, gabarits, revues, versions) : le profil maître, les gabarits, les
revues, les modifications, les versions et leurs images de pages d'une personne sont invisibles
pour une autre (listes vides, 404 sur leurs identifiants, aucune écriture possible), et le profil
de l'autre n'est jamais le sien."""

import httpx
from fastapi import FastAPI
from sqlalchemy import select

from app.db.models.accounts import User
from app.db.models.career import CvModification, CvReview, CvTemplate, CvVersion
from app.db.models.postings import JobPosting
from tests.sessions_support import act_as
from tests.support.profile import profile_data

API = "/api/v1"
OTHER = "autre-utilisatrice"
SECRET = "Modèle très secret de la première"
PNG = b"\x89PNG\r\n\x1a\n" + b"page-secrete"


async def _seed(app: FastAPI, user_id: str) -> dict[str, str]:
    """Un gabarit (avec sa page), une offre, sa revue, une modification et une version prête (avec
    sa page) du CV, rangés directement en base et dans le stockage."""
    storage = app.state.memory_providers.storage
    original = await storage.save(user_id, "cv", PNG, ".png")
    rendered = await storage.save(user_id, "cv", PNG, ".png")
    async with app.state.session_factory() as db:
        template = CvTemplate(
            user_id=user_id, document_id="d-1", name=SECRET, status="ready", page_count=1,
            page_size={"width_pt": 595, "height_pt": 842}, selectable=True,
            original_pages=[original],
        )  # fmt: skip
        posting = JobPosting(
            user_id=user_id, source="text", text="Offre", text_hash="h-cv", status="ready"
        )
        db.add_all([template, posting])
        await db.flush()
        review = CvReview(
            user_id=user_id, posting_id=posting.id, template_id=template.id, profile_version=1
        )
        db.add(review)
        await db.flush()
        modification = CvModification(
            user_id=user_id, review_id=review.id, ref="m1", section="experience", action="rewrite",
            before="avant", after="après", reason="raison", type="clarity", status="proposed",
            author="recruiter",
        )  # fmt: skip
        version = CvVersion(
            user_id=user_id, review_id=review.id, posting_id=posting.id, template_id=template.id,
            number=1, status="ready", content={}, filename="CV.pdf", original_page_count=1,
            page_images=[rendered],
        )  # fmt: skip
        db.add_all([modification, version])
        await db.commit()
        return {
            "template": template.id, "review": review.id, "version": version.id,
            "modification": modification.id, "posting": posting.id,
        }  # fmt: skip


def _probes(ids: dict[str, str]) -> tuple[tuple[str, str, str, dict[str, object]], ...]:
    """Chaque route qui prend l'identifiant d'un objet de la première : (méthode, chemin, code)."""
    review, version, template = ids["review"], ids["version"], ids["template"]
    return (
        ("GET", f"/cv/templates/{template}", "template_not_found", {}),
        ("GET", f"/cv/templates/{template}/pages/original/1", "template_not_found", {}),
        ("POST", f"/cv/templates/{template}/activate", "template_not_found", {}),
        ("DELETE", f"/cv/templates/{template}", "template_not_found", {}),
        ("GET", f"/cv/reviews/{review}", "review_not_found", {}),
        ("POST", f"/cv/reviews/{review}/generate", "review_not_found", {"json": {}}),
        (
            "PATCH",
            f"/cv/reviews/{review}/modifications",
            "review_not_found",
            {"json": {"ids": ["m1"], "status": "accepted"}},
        ),
        (
            "PATCH",
            f"/cv/modifications/{ids['modification']}",
            "modification_not_found",
            {"json": {"status": "refused"}},
        ),
        ("POST", "/cv/reviews", "posting_not_found", {"json": {"posting_id": ids["posting"]}}),
        ("GET", f"/cv/versions/{version}", "version_not_found", {}),
        ("GET", f"/cv/versions/{version}/pdf", "version_not_found", {}),
        ("GET", f"/cv/versions/{version}/pages/1", "version_not_found", {}),
    )


async def _assert_hidden(client: httpx.AsyncClient, ids: dict[str, str]) -> None:
    """Listes vides et 404 sur chaque identifiant de la première, sans rien en dire."""
    assert (await client.get(f"{API}/cv/templates")).json() == []
    assert (await client.get(f"{API}/cv/reviews")).json() == []
    assert (await client.get(f"{API}/cv/versions")).json() == []
    for method, path, code, kwargs in _probes(ids):
        r = await client.request(method, f"{API}{path}", **kwargs)
        assert (r.status_code, r.json()["error"]["code"]) == (404, code), (method, path)
        assert SECRET not in r.text and b"page-secrete" not in r.content


async def test_cv_of_another_account_is_invisible(client: httpx.AsyncClient, app: FastAPI) -> None:
    mine = await client.put(f"{API}/profile", json={"data": profile_data(), "base_version": None})
    assert mine.status_code == 200, mine.text
    ids = await _seed(app, app.state.local_user_id)
    assert [t["id"] for t in (await client.get(f"{API}/cv/templates")).json()] == [ids["template"]]
    assert (await client.get(f"{API}/cv/reviews/{ids['review']}")).status_code == 200
    # Contrôles positifs : la première lit bien ses deux pages (les 404 plus bas viennent donc
    # de l'isolation, pas d'une page qui n'existe pas).
    for page in (
        f"/cv/templates/{ids['template']}/pages/original/1",
        f"/cv/versions/{ids['version']}/pages/1",
    ):
        served = await client.get(f"{API}{page}")
        assert served.status_code == 200 and served.content == PNG, page

    async with app.state.session_factory() as db:
        db.add(User(id=OTHER, user_id=OTHER))
        await db.commit()
    act_as(app, OTHER)

    # Profil : ni version validée, ni brouillon, ni historique ; une écriture repart de zéro.
    state = (await client.get(f"{API}/profile")).json()
    assert state["validated"] is None and state["draft"] is None
    assert (await client.get(f"{API}/profile/versions")).json() == []
    await _assert_hidden(client, ids)
    # Son propre profil est une première version, pas la deuxième de l'autre (aucun conflit).
    own = await client.put(f"{API}/profile", json={"data": profile_data(), "base_version": None})
    assert own.status_code == 200 and own.json()["version"] == 1

    app.dependency_overrides.clear()
    first = (await client.get(f"{API}/profile")).json()["validated"]
    assert first["version"] == 1  # intact chez la première
    assert [t["id"] for t in (await client.get(f"{API}/cv/templates")).json()] == [ids["template"]]
    async with app.state.session_factory() as db:  # la décision de l'autre n'a rien écrit
        status = await db.scalar(select(CvModification.status))
    assert status == "proposed"
