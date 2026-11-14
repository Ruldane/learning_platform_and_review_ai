"""Port de la revue (`AgentCvReviewStore`, D129, D130) : contexte relu (profil figé, CV d'origine
dans l'ordre du gabarit, fiche entreprise seulement si fraîche), écritures idempotentes
(`save_company`, `save_proposals`, `render_version`, `close`) : un nœud rejoué n'écrit rien de
plus et une version n'est jamais rendue deux fois."""

from datetime import timedelta

import pytest
from sqlalchemy import func, select

from app.agents.tools.cv_review_port import ReviewReport
from app.agents.tools.review_schema import CompanyBrief
from app.core.errors import AppError
from app.db.models.career import CvModification, CvReview, CvVersion
from app.features.cv.schemas_reviews import GenerateIn
from app.features.cv.service.generate_start import generate
from app.features.cv.service.review_data import template_order
from app.features.cv.service.review_store import AgentCvReviewStore
from app.features.cv.service.reviews import start_review
from app.features.cv.service.runtime import CvRuntime
from tests.features.cv.reviews_support import (
    ITEMS,
    ResumeSpy,
    ready_posting,
    ready_template,
    validated_profile,
    wait_output,
)
from tests.features.cv.templates_support import ME, liberation_spec
from tests.support.text_renderer import TextHtmlRenderer

BRIEF = CompanyBrief(summary="Éditeur d'assistants.", values=["Clarté"], stack=["Python"])


@pytest.fixture
def store_real(cv_runtime: CvRuntime) -> AgentCvReviewStore:
    return AgentCvReviewStore(cv_runtime)


async def started(rt: CvRuntime) -> tuple[str, str]:
    await ready_template(rt, ME)
    await validated_profile(rt, ME)
    posting_id = await ready_posting(rt, ME)
    created = await start_review(rt, ME, posting_id)
    return created.review_id, created.session_id


async def count(rt: CvRuntime, model: type[CvModification] | type[CvVersion]) -> int:
    async with rt.session_factory() as db:
        return int((await db.execute(select(func.count()).select_from(model))).scalar_one())


async def test_context_reads_frozen_profile_and_template_order(
    cv_runtime: CvRuntime, store_real: AgentCvReviewStore
) -> None:
    review_id, _ = await started(cv_runtime)
    ctx = await store_real.context(ME, review_id)
    assert ctx.review_id == review_id and ctx.analysis is not None
    assert ctx.company == "Société Fictive" and ctx.company_brief is None
    assert ctx.posting_urls == ["https://jobs.example.org/offres/1"]
    assert ctx.profile.identity.name == "Camille Exemple"
    # ordre du gabarit fictif (colonne 1 puis 2) ; LinkedIn seul (x2) hors du CV d'origine
    keys = [s.key for s in ctx.base.sections]
    order = template_order(liberation_spec().model_dump(mode="json"))
    assert keys and keys == [key for key in order if key in keys]
    assert all(e.fact_id != "x2" for s in ctx.base.sections for e in s.entries)
    assert ctx.before.coverage.total == 4
    await validated_profile(cv_runtime, ME, version=2)
    assert (await store_real.context(ME, review_id)).profile == ctx.profile  # version figée
    with pytest.raises(AppError) as caught:
        await store_real.context(ME, "inconnue")
    assert caught.value.code == "review_not_found"


async def test_company_brief_only_when_fresh(
    cv_runtime: CvRuntime, store_real: AgentCvReviewStore
) -> None:
    review_id, session_id = await started(cv_runtime)
    await store_real.save_company(ME, session_id, "Société Fictive SAS", BRIEF, ["u"], "lever")
    await store_real.save_company(ME, session_id, "Société Fictive SAS", BRIEF, ["u"], "lever")
    ctx = await store_real.context(ME, review_id)
    assert ctx.company_brief == BRIEF and ctx.company_ats == "lever"
    async with cv_runtime.session_factory() as db:
        review = await db.get(CvReview, review_id)
        assert review is not None and review.company_id is not None
    now = cv_runtime.now()
    cv_runtime.now = lambda: now + timedelta(days=30)
    stale = await store_real.context(ME, review_id)
    assert stale.company_brief is None and stale.company_ats == "lever"


async def test_save_proposals_is_idempotent(
    cv_runtime: CvRuntime, store_real: AgentCvReviewStore
) -> None:
    review_id, session_id = await started(cv_runtime)
    report = ReviewReport(ats="lever")
    first = await store_real.save_proposals(ME, session_id, review_id, ITEMS, ["AWS"], report)
    again = await store_real.save_proposals(ME, session_id, review_id, ITEMS, ["AWS"], report)
    assert first == again == 4  # la proposition partie vers l'écart n'est jamais rangée
    assert await count(cv_runtime, CvModification) == 4
    async with cv_runtime.session_factory() as db:
        review = await db.get(CvReview, review_id)
    assert review is not None
    assert (review.status, review.keywords_to_gap, review.report["ats"]) == (  # type: ignore[index]
        "proposed",
        ["AWS"],
        "lever",
    )


async def test_generate_replayed_writes_one_version(
    cv_runtime: CvRuntime, store_real: AgentCvReviewStore
) -> None:
    review_id, session_id = await started(cv_runtime)
    await store_real.save_proposals(ME, session_id, review_id, ITEMS, [], ReviewReport())
    await wait_output(cv_runtime, session_id)
    cv_runtime.resumer = ResumeSpy(cv_runtime, render=False)
    version_id = (await generate(cv_runtime, ME, review_id, GenerateIn())).version_id
    renderer = cv_runtime.html_pdf
    assert isinstance(renderer, TextHtmlRenderer)
    renderer.documents.clear()
    first = await store_real.render_version(ME, version_id)
    replayed = await store_real.render_version(ME, version_id)  # nœud rejoué après un arrêt
    assert first == replayed and first.status == "ready"
    assert len(renderer.documents) == 1 and await count(cv_runtime, CvVersion) == 1
    assert first.filename.startswith("CV_Camille_Exemple")
    with pytest.raises(AppError) as caught:
        await store_real.render_version(ME, "inconnue")
    assert caught.value.code == "version_not_found"


async def test_close_is_idempotent(cv_runtime: CvRuntime, store_real: AgentCvReviewStore) -> None:
    review_id, _ = await started(cv_runtime)
    await store_real.close(ME, review_id)
    await store_real.close(ME, review_id)
    async with cv_runtime.session_factory() as db:
        review = await db.get(CvReview, review_id)
    assert review is not None and review.status == "done"
