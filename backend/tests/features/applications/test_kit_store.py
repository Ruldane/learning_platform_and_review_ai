"""Port réel du kit (`AgentKitStore`, D143) : le contexte lu en base, l'écriture des pièces
idempotente par (fiche, pièce, session) et sûre sous écritures parallèles, le dossier de
l'entreprise dont les pages gardent leur rang de citation (Review Focus du kit)."""

import asyncio
from datetime import date, timedelta

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import delete, func, select

from app.agents.tools.kit_schema import KIT_KINDS
from app.core.errors import AppError
from app.db.models.applications import KitItem
from app.db.models.career import MasterProfile
from app.db.models.postings import Company, JobPosting
from app.features.applications.service.kit_store import AgentKitStore
from app.features.postings.service.rules import company_key
from tests.features.applications.conftest import API, NOW, add_posting, add_version
from tests.features.applications.kit_support import (
    COMPANY,
    CONTACT,
    OTHER_SESSION,
    POSTING,
    SESSION,
    TITLE,
    add_profile,
    dossier,
    get_kit,
    kit_events,
    kit_store,
    ready_application,
    save,
    sources,
)

pytestmark = pytest.mark.usefixtures("client")


async def rows(app: FastAPI, application_id: str) -> list[KitItem]:
    async with app.state.session_factory() as db:
        stmt = select(KitItem).where(KitItem.application_id == application_id)
        return list((await db.execute(stmt)).scalars())


async def test_context_reads_the_application_profile_and_contact(
    client: httpx.AsyncClient, app: FastAPI, me: str
) -> None:
    application_id = await ready_application(client, app)
    ctx = await kit_store(app).context(me, application_id)
    assert (ctx.application_id, ctx.company, ctx.title, ctx.contact) == (
        application_id,
        COMPANY,
        TITLE,
        CONTACT,
    )
    assert ctx.posting_text == POSTING.strip()
    assert (ctx.today, ctx.language, ctx.keep) == (date(2026, 11, 15), "fr", [])
    assert ctx.profile.identity.name == "Camille Exemple"
    assert ctx.company_dossier is None and ctx.cv_version is None
    # Analyse minimale de la copie figée : l'entreprise et l'intitulé de la fiche, rien d'inventé.
    assert (ctx.analysis.title, ctx.analysis.company) == (TITLE, COMPANY)
    assert not ctx.analysis.requirements and not ctx.analysis.keywords


async def test_context_uses_the_linked_posting_analysis_and_ready_version(
    client: httpx.AsyncClient, app: FastAPI, me: str
) -> None:
    posting = await add_posting(app, language="en", text=POSTING)
    async with app.state.session_factory() as db:
        row = await db.get(JobPosting, posting)
        assert row is not None
        row.analysis = {**(row.analysis or {}), "is_job_posting": True, "level": "senior"}
        await db.commit()
    await add_version(app, posting, number=1)
    await add_version(app, posting, number=2)
    await add_profile(app)
    application_id = (
        await client.post(API, json={"posting_id": posting, "company": COMPANY, "title": TITLE})
    ).json()["application"]["id"]
    ctx = await kit_store(app).context(me, application_id)
    assert (ctx.language, ctx.analysis.level) == ("en", "senior")
    assert ctx.cv_version is not None and ctx.cv_version.number == 2  # la plus récente prête
    assert ctx.posting_text == POSTING.strip()


async def test_context_needs_a_posting_and_a_profile(
    client: httpx.AsyncClient, app: FastAPI, me: str
) -> None:
    store = kit_store(app)
    no_posting = await ready_application(client, app, posting_text=None, title="Sans offre")
    with pytest.raises(AppError) as err:
        await store.context(me, no_posting)
    assert (err.value.code, err.value.status_code) == ("posting_required", 409)
    async with app.state.session_factory() as db:
        await db.execute(delete(MasterProfile))
        await db.commit()
    no_profile = await ready_application(client, app, profile=False, title="Sans profil")
    with pytest.raises(AppError) as err:
        await store.context(me, no_profile)
    assert (err.value.code, err.value.status_code) == ("profile_required", 409)
    with pytest.raises(AppError) as err:
        await store.context(me, "00000000-0000-4000-8000-000000000000")
    assert err.value.code == "application_not_found"


async def test_context_never_reads_another_users_application(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    application_id = await ready_application(client, app)
    with pytest.raises(AppError) as err:
        await kit_store(app).context("autre-utilisatrice", application_id)
    assert err.value.code == "application_not_found"


async def test_company_dossier_sources_come_back_in_rank_order(
    client: httpx.AsyncClient, app: FastAPI, me: str
) -> None:
    """`[n]` d'un dossier repris se lit rang + 1 : l'ordre rangé est celui lu, jamais retrié."""
    application_id = await ready_application(client, app)
    store = kit_store(app)
    ordered = sources(5)[::-1]  # ni alphabétique ni croissant : seul le rang compte
    await store.save_dossier(me, SESSION, COMPANY, dossier(), ordered)
    ctx = await store.context(me, application_id)
    assert ctx.company_dossier is not None
    assert [source.url for source in ctx.company_dossier_sources] == [s.url for s in ordered]
    assert ctx.company_dossier_sources == ordered


async def test_dossier_older_than_30_days_is_not_reused(
    client: httpx.AsyncClient, app: FastAPI, me: str
) -> None:
    application_id = await ready_application(client, app)
    store = kit_store(app)
    await store.save_dossier(me, SESSION, COMPANY, dossier(), sources())
    assert (await store.context(me, application_id)).company_dossier is not None
    app.state.career.applications.now = lambda: NOW + timedelta(days=30, minutes=1)
    ctx = await store.context(me, application_id)
    assert ctx.company_dossier is None and ctx.company_dossier_sources == []
    app.state.career.applications.now = lambda: NOW + timedelta(days=29)
    assert (await store.context(me, application_id)).company_dossier is not None


async def test_save_dossier_is_idempotent_per_session(
    client: httpx.AsyncClient, app: FastAPI, me: str
) -> None:
    await ready_application(client, app)
    store = kit_store(app)
    await store.save_dossier(me, SESSION, COMPANY, dossier(), sources(2))
    first = await _company(app)
    app.state.career.applications.now = lambda: NOW + timedelta(days=1)
    await store.save_dossier(me, SESSION, COMPANY, dossier(), sources(3))  # rejeu de la session
    again = await _company(app)
    assert (again.dossier_at, again.dossier_sources) == (first.dossier_at, first.dossier_sources)
    await store.save_dossier(me, OTHER_SESSION, COMPANY, dossier(), sources(3))  # nouvelle session
    newer = await _company(app)
    assert len(newer.dossier_sources) == 3 and newer.dossier_at is not None
    assert first.dossier_at is not None and newer.dossier_at > first.dossier_at
    async with app.state.session_factory() as db:
        count = (await db.execute(select(func.count()).select_from(Company))).scalar_one()
    assert count == 1  # la fiche entreprise n'est jamais dédoublée


async def _company(app: FastAPI) -> Company:
    async with app.state.session_factory() as db:
        stmt = select(Company).where(Company.name_norm == company_key(COMPANY))
        row = (await db.execute(stmt)).scalar_one()
        db.expunge(row)
        return row


async def test_save_piece_is_idempotent_per_application_kind_and_session(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    application_id = await ready_application(client, app)
    first = await save(app, application_id, "letter", content="Premier texte.")
    again = await save(app, application_id, "letter", content="Texte rejoué.")
    assert again == first
    [row] = await rows(app, application_id)
    assert (row.content, row.session_id, row.status) == ("Premier texte.", SESSION, "ready")
    newer = await save(app, application_id, "letter", session=OTHER_SESSION, content="Refait.")
    assert newer == first  # la même ligne, remplacée par la nouvelle session
    [row] = await rows(app, application_id)
    assert (row.content, row.session_id, row.edited) == ("Refait.", OTHER_SESSION, False)


async def test_save_piece_never_overwrites_a_piece_january_edited(
    client: httpx.AsyncClient, app: FastAPI, me: str
) -> None:
    application_id = await ready_application(client, app)
    await save(app, application_id, "letter", content="Version du kit.")
    r = await client.patch(f"{API}/{application_id}/kit/letter", json={"content": "Ma version."})
    assert r.status_code == 200
    assert (await kit_store(app).context(me, application_id)).keep == ["letter"]
    kept = await save(app, application_id, "letter", session=OTHER_SESSION, content="Refaite.")
    [row] = await rows(app, application_id)
    assert (kept, row.content, row.edited, row.session_id) == (row.id, "Ma version.", True, SESSION)


async def test_seven_parallel_saves_and_replays_make_seven_rows(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    """Les sept branches rangent en même temps, avec des rejeux : une ligne par pièce, jamais
    deux, les mêmes identifiants, l'événement de fin une seule fois."""
    application_id = await ready_application(client, app)
    calls = [
        save(app, application_id, kind, content=f"Texte {kind} {attempt}")
        for attempt in range(3)  # chaque pièce arrive trois fois : branche + deux rejeux
        for kind in KIT_KINDS
    ]
    ids = await asyncio.gather(*calls)
    stored = await rows(app, application_id)
    assert len(stored) == 7 and {row.kind for row in stored} == set(KIT_KINDS)
    assert {row.id for row in stored} == set(ids) and len(set(ids)) == 7
    assert all(row.session_id == SESSION for row in stored)
    assert len(await kit_events(app, application_id)) == 1


async def test_parallel_saves_of_the_same_piece_by_two_sessions_keep_one_row(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    application_id = await ready_application(client, app)
    await asyncio.gather(
        *[
            save(app, application_id, "pitch", session=session, content=f"Texte {session[:2]}")
            for session in (SESSION, OTHER_SESSION) * 4
        ]
    )
    [row] = await rows(app, application_id)
    assert row.session_id in (SESSION, OTHER_SESSION)


async def test_company_brief_keeps_the_pages_it_cites_in_rank_order(
    client: httpx.AsyncClient, app: FastAPI, me: str
) -> None:
    application_id = await ready_application(client, app)
    ordered = sources(3)[::-1]
    await kit_store(app).save_dossier(me, SESSION, COMPANY, dossier(), ordered)
    await save(app, application_id, "company_brief", meta={"sources": 3})
    brief = next(
        i for i in (await get_kit(client, application_id))["items"] if i["kind"] == "company_brief"
    )
    assert [(s["rank"], s["url"]) for s in brief["sources"]] == [
        (rank, source.url) for rank, source in enumerate(ordered, 1)
    ]
    # Un dossier refait plus tard (autre fiche, autre session) ne change pas les pages rangées.
    await kit_store(app).save_dossier(me, OTHER_SESSION, COMPANY, dossier(), sources(1))
    again = next(
        i for i in (await get_kit(client, application_id))["items"] if i["kind"] == "company_brief"
    )
    assert [s["url"] for s in again["sources"]] == [s.url for s in ordered]


async def test_the_port_is_wired_into_the_career_runtimes(app: FastAPI) -> None:
    assert isinstance(app.state.career.kit_store, AgentKitStore)


async def test_kit_cv_piece_uses_sent_version(
    client: httpx.AsyncClient, app: FastAPI, me: str
) -> None:
    """M1 : une fiche postulée a figé la version n° 2 ; la version n° 3, prête ensuite, n'est pas
    celle qui a été envoyée : la pièce `cv` relancée lit la version figée."""
    posting = await add_posting(app, text=POSTING)
    v1 = await add_version(app, posting, number=1)
    v2 = await add_version(app, posting, number=2)
    await add_profile(app)
    body = {"posting_id": posting, "company": COMPANY, "title": TITLE, "status": "applied"}
    application_id = (await client.post(API, json=body)).json()["application"]["id"]
    v3 = await add_version(app, posting, number=3)
    ctx = await kit_store(app).context(me, application_id)
    assert ctx.cv_version is not None
    assert (ctx.cv_version.version_id, ctx.cv_version.number) == (v2, 2)
    assert v1 != v2 != v3
    # « À postuler » : la version prête la plus récente, comme avant.
    other = await add_posting(app, company="Autre SA", title="Poste", text=POSTING)
    await add_version(app, other, number=1)
    draft = (
        await client.post(API, json={"posting_id": other, "company": "Autre SA", "title": "Poste"})
    ).json()["application"]["id"]
    latest = await add_version(app, other, number=2)
    ctx = await kit_store(app).context(me, draft)
    assert ctx.cv_version is not None and ctx.cv_version.version_id == latest
