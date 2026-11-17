"""Routeur `cv` (paquet : profil, gabarits, revues, versions) : le profil maître, les gabarits, les
revues et les versions d'une personne sont invisibles pour une autre (listes vides, 404 sur leurs
identifiants, aucune écriture possible), et le profil de l'autre n'est jamais le sien."""

import httpx
from fastapi import FastAPI

from app.db.models.accounts import User
from app.db.models.career import CvReview, CvTemplate, CvVersion
from app.db.models.postings import JobPosting
from tests.sessions_support import act_as
from tests.support.profile import profile_data

API = "/api/v1"
OTHER = "autre-utilisatrice"
SECRET = "Modèle très secret de la première"


async def _seed(app: FastAPI, user_id: str) -> dict[str, str]:
    """Un gabarit, une offre, sa revue et une version du CV, rangés directement en base."""
    async with app.state.session_factory() as db:
        template = CvTemplate(
            user_id=user_id, document_id="d-1", name=SECRET, status="ready", page_count=1,
            page_size={"width_pt": 595, "height_pt": 842}, selectable=True,
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
        version = CvVersion(
            user_id=user_id, review_id=review.id, posting_id=posting.id, template_id=template.id,
            number=1, status="ready", content={}, filename="CV.pdf", original_page_count=1,
        )  # fmt: skip
        db.add(version)
        await db.commit()
        return {"template": template.id, "review": review.id, "version": version.id}


async def test_cv_of_another_account_is_invisible(client: httpx.AsyncClient, app: FastAPI) -> None:
    mine = await client.put(f"{API}/profile", json={"data": profile_data(), "base_version": None})
    assert mine.status_code == 200, mine.text
    ids = await _seed(app, app.state.local_user_id)
    assert [t["id"] for t in (await client.get(f"{API}/cv/templates")).json()] == [ids["template"]]
    assert (await client.get(f"{API}/cv/reviews/{ids['review']}")).status_code == 200

    async with app.state.session_factory() as db:
        db.add(User(id=OTHER, user_id=OTHER))
        await db.commit()
    act_as(app, OTHER)

    # Profil : ni version validée, ni brouillon, ni historique ; une écriture repart de zéro.
    state = (await client.get(f"{API}/profile")).json()
    assert state["validated"] is None and state["draft"] is None
    assert (await client.get(f"{API}/profile/versions")).json() == []
    # Listes vides.
    assert (await client.get(f"{API}/cv/templates")).json() == []
    assert (await client.get(f"{API}/cv/reviews")).json() == []
    assert (await client.get(f"{API}/cv/versions")).json() == []
    # 404 sur chaque identifiant de la première, sans rien en dire.
    probes = (
        ("GET", f"/cv/templates/{ids['template']}", "template_not_found", {}),
        ("POST", f"/cv/templates/{ids['template']}/activate", "template_not_found", {}),
        ("DELETE", f"/cv/templates/{ids['template']}", "template_not_found", {}),
        ("GET", f"/cv/reviews/{ids['review']}", "review_not_found", {}),
        ("POST", f"/cv/reviews/{ids['review']}/generate", "review_not_found", {"json": {}}),
        (
            "PATCH",
            f"/cv/reviews/{ids['review']}/modifications",
            "review_not_found",
            {"json": {"ids": ["m1"], "status": "accepted"}},
        ),
        ("GET", f"/cv/versions/{ids['version']}", "version_not_found", {}),
        ("GET", f"/cv/versions/{ids['version']}/pdf", "version_not_found", {}),
    )
    for method, path, code, kwargs in probes:
        r = await client.request(method, f"{API}{path}", **kwargs)
        assert (r.status_code, r.json()["error"]["code"]) == (404, code), (method, path)
        assert SECRET not in r.text
    # Son propre profil est une première version, pas la deuxième de l'autre (aucun conflit).
    own = await client.put(f"{API}/profile", json={"data": profile_data(), "base_version": None})
    assert own.status_code == 200 and own.json()["version"] == 1

    app.dependency_overrides.clear()
    first = (await client.get(f"{API}/profile")).json()["validated"]
    assert first["version"] == 1  # intact chez la première
    assert [t["id"] for t in (await client.get(f"{API}/cv/templates")).json()] == [ids["template"]]
