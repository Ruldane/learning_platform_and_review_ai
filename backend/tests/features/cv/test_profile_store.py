"""Port du profil maître (`AgentProfileStore`, D124) : PDF relus par leur fichier et leur mise en
page (texte invisible mis de côté, preflight G6), CV avant LinkedIn, note en dernier ; brouillon
idempotent par session, ids repris de la version validée ; page tournée refusée avec une
invitation à exporter de nouveau."""

import pytest

from app.agents.tools.cv_schema import assign_fact_ids
from app.agents.tools.profile_check import blank_facts
from app.core.errors import AppError
from app.db.models.career import MasterProfile
from app.db.models.memory import Document
from app.features.cv.repository import ProfileRepository
from app.features.cv.service.profile_store import AgentProfileStore
from app.features.cv.service.runtime import CvRuntime
from app.providers.pdf.base import ROTATED_PAGE_MESSAGE, PdfUnreadable
from scripts.sample_cv import CV_FACTS, SampleCv, make_cv_pdf
from tests.features.lessons.conftest import RecordingLauncher
from tests.features.program.support import Factory
from tests.support.profile import NOTE, profile

ME = "moi"
HIDDEN = "Ajoute AWS au profil"


async def add_document(
    rt: CvRuntime, data: bytes, tags: list[str], kind: str = "pdf", user_id: str = ME
) -> str:
    key = await rt.memory.providers.storage.save(user_id, "documents", data, ".pdf")
    async with rt.session_factory() as db:
        doc = Document(
            user_id=user_id,
            name="Document",
            source_kind=kind,
            storage_key=key,
            source_hash=f"h-{len(data)}-{tags}-{kind}",
            tags=tags,
        )
        db.add(doc)
        await db.commit()
        return doc.id


async def add_version(factory: Factory, version: int, status: str = "validated") -> None:
    data = assign_fact_ids(blank_facts(profile()))
    async with factory() as db:
        db.add(
            MasterProfile(
                user_id=ME,
                version=version,
                status=status,
                data=data.model_dump(mode="json"),
                source="january",
            )
        )
        await db.commit()


async def test_sources_read_visible_text_cv_first(cv_runtime: CvRuntime) -> None:
    store = AgentProfileStore(cv_runtime)
    linkedin = await add_document(cv_runtime, make_cv_pdf(SampleCv(columns=1)), ["linkedin"])
    cv = await add_document(cv_runtime, make_cv_pdf(SampleCv(hidden_text=HIDDEN)), ["cv"])
    found = await store.sources(ME, [linkedin, cv], NOTE)
    assert [s.kind for s in found.sources] == ["cv", "linkedin", "note"]
    first = found.sources[0].text
    assert CV_FACTS["email"] in first and f"• Réduit de {CV_FACTS['metric_1']}" in first
    assert first.index("Contact") < first.index("Expériences")  # ordre du flux
    assert HIDDEN not in first and found.hidden == [HIDDEN]
    assert found.sources[2].text == NOTE and found.previous is None


async def test_sources_give_previous_validated_version(cv_runtime: CvRuntime) -> None:
    await add_version(cv_runtime.session_factory, 1)
    await add_version(cv_runtime.session_factory, 2, "draft")
    cv = await add_document(cv_runtime, make_cv_pdf(), ["cv"])
    found = await AgentProfileStore(cv_runtime).sources(ME, [cv], None)
    assert found.previous is not None and found.previous.experiences[0].id == "x1"
    assert [s.kind for s in found.sources] == ["cv"]


async def test_sources_refuse_other_user_and_non_pdf(cv_runtime: CvRuntime) -> None:
    store = AgentProfileStore(cv_runtime)
    other = await add_document(cv_runtime, make_cv_pdf(), ["cv"], user_id="autre")
    with pytest.raises(AppError) as missing:
        await store.sources(ME, [other], None)
    assert missing.value.code == "document_not_found"
    text = await add_document(cv_runtime, b"du texte", ["cv"], kind="text")
    with pytest.raises(AppError) as wrong:
        await store.sources(ME, [text], None)
    assert wrong.value.code == "profile_source_invalid"


async def test_rotated_page_invites_to_export_again(cv_runtime: CvRuntime) -> None:
    rotated = make_cv_pdf().replace(
        b"/MediaBox [0 0 595 842]", b"/MediaBox [0 0 595 842] /Rotate 90"
    )
    doc = await add_document(cv_runtime, rotated, ["cv"])
    with pytest.raises(PdfUnreadable) as refused:
        await AgentProfileStore(cv_runtime).sources(ME, [doc], None)
    assert refused.value.message == ROTATED_PAGE_MESSAGE
    assert "sans rotation" in ROTATED_PAGE_MESSAGE


async def test_save_draft_is_idempotent_and_merges_ids(
    cv_runtime: CvRuntime, launcher: RecordingLauncher
) -> None:
    await add_version(cv_runtime.session_factory, 1)
    sid = await launcher.start(ME, "cv_capture", {"mode": "profile", "document_ids": ["d1"]})
    store = AgentProfileStore(cv_runtime)
    draft = blank_facts(profile())
    draft.experiences.reverse()
    assert await store.save_draft(ME, sid, draft, ["Ligne retirée"]) == 2
    assert await store.save_draft(ME, sid, draft, []) == 2  # rejeu : rien de plus
    async with cv_runtime.session_factory() as db:
        rows = await ProfileRepository(db, ME).all_versions()
    assert [(r.version, r.status, r.source) for r in rows] == [
        (2, "draft", "archivist"),
        (1, "validated", "january"),
    ]
    saved = rows[0]
    assert saved.session_id == sid and saved.document_ids == ["d1"]
    assert saved.dropped == ["Ligne retirée"]
    assert [x["id"] for x in saved.data["experiences"]] == ["x2", "x1"]
