"""API des revues de CV (D130) : lancement figé sur le profil validé et le gabarit actif, refus
lisibles (profil, gabarit, offre, revue en cours), revue rendue avec ses indicateurs avant, ses
modifications et son rapport, statut qui suit la session, rien du CV ni de l'offre dans les
journaux."""

import logging

import httpx
import pytest
from fastapi import FastAPI

from app.db.models.career import CvReview
from app.features.cv.service.runtime import CvRuntime
from scripts.sample_cv import CV_FACTS
from tests.features.cv.reviews_support import (
    API,
    EDITED,
    SECRET_LINE,
    ResumeSpy,
    decide,
    mods,
    open_review,
    post_generate,
    ready_posting,
    ready_template,
    review,
    set_session,
    validated_profile,
)
from tests.features.lessons.conftest import RecordingLauncher
from tests.support.text_renderer import TextHtmlRenderer

REVIEWS = f"{API}/cv/reviews"


def rt_of(app: FastAPI) -> CvRuntime:
    runtime: CvRuntime = app.state.career.cv
    return runtime


async def test_start_review_requires_profile_template_and_ready_posting(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher
) -> None:
    rt, me = rt_of(app), app.state.local_user_id
    analyzing = await ready_posting(rt, me, status="analyzing", analysis=None)
    missing = await client.post(REVIEWS, json={"posting_id": "inconnue"})
    assert missing.status_code == 404
    r = await client.post(REVIEWS, json={"posting_id": analyzing})
    assert (r.status_code, r.json()["error"]["code"]) == (409, "posting_not_ready")
    posting_id = await ready_posting(rt, me, text="Autre texte d'offre")
    r = await client.post(REVIEWS, json={"posting_id": posting_id})
    assert (r.status_code, r.json()["error"]["code"]) == (409, "profile_required")
    await validated_profile(rt, me)
    r = await client.post(REVIEWS, json={"posting_id": posting_id})
    assert (r.status_code, r.json()["error"]["code"]) == (409, "template_required")
    template_id = await ready_template(rt, me)
    launcher_spy.started.clear()
    r = await client.post(REVIEWS, json={"posting_id": posting_id})
    assert r.status_code == 202, r.text
    body = r.json()
    assert launcher_spy.started == [("cv_review", {"review_id": body["review_id"]})]
    async with app.state.session_factory() as db:
        row = await db.get(CvReview, body["review_id"])
        assert row is not None
        assert (row.template_id, row.profile_version, row.status) == (template_id, 1, "running")
    shown = await review(client, body["review_id"])
    assert (shown["status"], shown["session_id"], shown["waiting_output"]) == (
        "running",
        body["session_id"],
        False,
    )
    before = shown["before"]
    assert before["total"] == 4 and 0 <= before["coverage_percent"] <= 100
    assert [c["id"] for c in before["checks"]] == [
        "selectable_text",
        "reading_order",
        "standard_headings",
        "contact_in_body",
        "font_sizes",
    ]


async def test_invalid_body_is_422_without_echo(
    client: httpx.AsyncClient, launcher_spy: RecordingLauncher
) -> None:
    r = await client.post(REVIEWS, json={"posting_id": "x" * 40})
    assert r.status_code == 422
    assert r.json()["error"]["details"] == {"fields": ["posting_id"]}
    assert "x" * 40 not in r.text


async def test_second_review_on_same_posting_is_409(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher
) -> None:
    review_id, _ = await open_review(client, app)
    posting_id = (await review(client, review_id))["posting_id"]
    r = await client.post(REVIEWS, json={"posting_id": posting_id})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "review_in_progress"
    assert r.json()["error"]["details"] == {"review_id": review_id}
    listed = (await client.get(REVIEWS, params={"posting_id": posting_id})).json()
    assert [item["id"] for item in listed] == [review_id]


async def test_review_lists_modifications_report_and_gap(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher
) -> None:
    review_id, _ = await open_review(client, app)
    shown = await review(client, review_id)
    assert shown["status"] == "proposed" and shown["waiting_output"]
    by_ref = {m["ref"]: m for m in shown["modifications"]}
    assert sorted(by_ref) == ["a1", "a2", "r1", "r2"]  # `to_gap` jamais rangée
    assert (by_ref["a1"]["status"], by_ref["a1"]["author"]) == ("proposed", "ats_reader")
    assert by_ref["a1"]["before"] == "Réduit les coûts de 30 %"
    assert by_ref["r1"]["status"] == "to_confirm" and by_ref["r1"]["author"] == "recruiter"
    assert by_ref["r1"]["blocks"] == ["Chiffre absent de ton profil"]
    assert by_ref["a2"]["before"] == ""  # ajout : rien dans le CV d'origine
    assert shown["gap_terms"] == ["AWS"]
    assert shown["report"]["ats"] == "greenhouse"


async def test_closed_session_settles_review_to_failed(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher
) -> None:
    review_id, session_id = await open_review(client, app, proposed=False)
    await set_session(rt_of(app), session_id, "failed")
    shown = await review(client, review_id)
    assert shown["status"] == "failed" and not shown["waiting_output"]
    posting_id = shown["posting_id"]
    again = await client.post(REVIEWS, json={"posting_id": posting_id})
    assert again.status_code == 202  # une revue en échec ne bloque pas la suivante


async def test_finished_review_rejects_decisions(
    client: httpx.AsyncClient, app: FastAPI, launcher_spy: RecordingLauncher
) -> None:
    review_id, _ = await open_review(client, app)
    await app.state.career.cv_review.close(app.state.local_user_id, review_id)
    mod_id = (await mods(client, review_id))["a1"]["id"]
    r = await decide(client, mod_id, "accepted")
    assert (r.status_code, r.json()["error"]["code"]) == (409, "review_closed")
    r = await post_generate(client, review_id)
    assert (r.status_code, r.json()["error"]["code"]) == (409, "review_closed")


async def test_review_data_never_logged(
    client: httpx.AsyncClient,
    app: FastAPI,
    launcher_spy: RecordingLauncher,
    resume_spy: ResumeSpy,
    fake_renderer: TextHtmlRenderer,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    caplog.set_level(logging.DEBUG, logger="app")
    review_id, _ = await open_review(client, app)
    by_ref = await mods(client, review_id)
    await decide(client, by_ref["a1"]["id"], "accepted", after=EDITED)
    await decide(client, by_ref["r1"]["id"], "accepted", confirm=True)
    r = await post_generate(client, review_id)
    assert r.status_code == 202, r.text
    await client.get(f"{API}/cv/versions/{r.json()['version_id']}/pdf")
    logs = "\n".join(record.getMessage() for record in caplog.records)
    for secret in (
        CV_FACTS["name"],
        "Camille",
        "Société Fictive",
        "Fictive",
        "CV_",
        SECRET_LINE,
        EDITED,
        "Réduit les coûts",
        "AI Product Engineer",
        "Kubernetes",
        "example.org",
    ):
        assert secret not in logs, secret
