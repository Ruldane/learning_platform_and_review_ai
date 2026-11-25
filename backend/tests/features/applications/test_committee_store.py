"""Port réel du comité (`AgentCommitteeStore`, D147) : contexte lu en base, issue rangée une seule
fois par session, événement du fil, et l'avant et l'après d'une seconde exécution (F19)."""

from datetime import timedelta

import httpx
import pytest
from fastapi import FastAPI

from app.agents.tools.committee_schema import CommitteeContext
from app.core.errors import AppError
from tests.features.applications.committee_support import (
    COMPANY,
    NOW,
    ROOT,
    UNKNOWN,
    committee_store,
    launch,
    ready_committee,
    run_row,
    save_done,
    spy,
    store_company,
    synthesis_of,
    votes_of,
)

pytestmark = pytest.mark.usefixtures("client")


async def _ctx(app: FastAPI, run_id: str) -> CommitteeContext:
    return await committee_store(app).context(str(app.state.local_user_id), run_id)


async def test_context_reads_cv_posting_profile_and_terms(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    _, version = await ready_committee(client, app)
    started = await launch(client, version)
    ctx = await _ctx(app, started["run_id"])
    assert "AI Engineer Python" in ctx.cv_text and "Camille Exemple" not in ctx.cv_text
    assert ctx.posting_text == "Offre : agents Python et LangGraph."
    assert (ctx.company, ctx.title) == (COMPANY, "Développeuse IA")  # la fiche de l'offre
    assert ctx.analysis.title == "AI Product Engineer" and ctx.profile.skills
    assert "LangGraph" in ctx.ats_terms.missing and ctx.dossier is None and ctx.size == "unknown"


async def test_context_without_fiche_uses_the_posting(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    _, version = await ready_committee(client, app, fiche=False)
    started = await launch(client, version)
    ctx = await _ctx(app, started["run_id"])
    assert (ctx.company, ctx.title) == ("Société Fictive", "Développeuse IA")


async def test_dossier_gives_the_size_when_recent(client: httpx.AsyncClient, app: FastAPI) -> None:
    _, version = await ready_committee(client, app)
    await store_company(app, COMPANY, "large_company", at=NOW - timedelta(days=29))
    started = await launch(client, version)
    ctx = await _ctx(app, started["run_id"])
    assert ctx.size == "large_company" and ctx.dossier is not None


async def test_old_dossier_is_not_used(client: httpx.AsyncClient, app: FastAPI) -> None:
    _, version = await ready_committee(client, app)
    await store_company(app, COMPANY, "startup", at=NOW - timedelta(days=31))
    started = await launch(client, version)
    ctx = await _ctx(app, started["run_id"])
    assert ctx.size == "unknown" and ctx.dossier is None


async def test_context_refusals(client: httpx.AsyncClient, app: FastAPI) -> None:
    _, version = await ready_committee(client, app)
    with pytest.raises(AppError) as unknown:
        await _ctx(app, UNKNOWN)
    assert (unknown.value.status_code, unknown.value.code) == (404, "committee_not_found")
    started = await launch(client, version)
    other = committee_store(app)
    with pytest.raises(AppError) as foreign:
        await other.context("autre-utilisatrice", started["run_id"])
    assert foreign.value.code == "committee_not_found"


async def test_save_is_idempotent_per_session(client: httpx.AsyncClient, app: FastAPI) -> None:
    posting, version = await ready_committee(client, app)
    started = await launch(client, version)
    await save_done(app, started, votes_of("yes", "yes", "yes", "no"), synthesis_of("yes"))
    await save_done(app, started, votes_of("no", "no", "no", "no"), synthesis_of("no"))
    row = await run_row(app, started["run_id"])
    assert (row.status, row.verdict) == ("done", "yes")
    assert [v["vote"] for v in row.votes] == ["yes", "yes", "yes", "no"]
    applications = (await client.get(f"{ROOT}/applications", params={"posting_id": posting})).json()
    [application] = applications
    events = [
        e
        for e in (await client.get(f"{ROOT}/applications/{application['id']}")).json()["events"]
        if e["kind"] == "committee"
    ]
    assert len(events) == 1  # un seul événement, malgré le rejeu
    assert "voted yes" in events[0]["text"] and "3 yes, 1 no, 0 maybe" in events[0]["text"]
    assert row.application_id == application["id"]


async def test_no_event_without_fiche(client: httpx.AsyncClient, app: FastAPI) -> None:
    _, version = await ready_committee(client, app, fiche=False)
    started = await launch(client, version)
    await save_done(app, started, votes_of("yes", "yes", "yes", "yes"), synthesis_of("yes"))
    row = await run_row(app, started["run_id"])
    assert (row.status, row.application_id) == ("done", None)  # aucune fiche : aucun événement


async def test_second_run_shows_diff(client: httpx.AsyncClient, app: FastAPI) -> None:
    """F19 : relancer le comité après correction montre l'avant et l'après."""
    posting, version = await ready_committee(client, app)
    first = await launch(client, version)
    await save_done(
        app,
        first,
        votes_of("no", "no", "maybe", "no"),
        synthesis_of(
            "no", "Aucun mot clé LangGraph dans le CV", "Résultat chiffré enfoui", "Peu d'équipe"
        ),
    )
    await spy(app).end(str(app.state.local_user_id), first["session_id"])
    alone = (await client.get(f"{ROOT}/committee/{first['run_id']}")).json()
    assert alone["previous"] is None  # la première exécution n'a pas d'avant
    second = await launch(client, version)
    assert (await run_row(app, second["run_id"])).previous_id == first["run_id"]
    running = (await client.get(f"{ROOT}/committee/{second['run_id']}")).json()
    assert running["status"] == "running" and running["previous"] is None
    await save_done(
        app,
        second,
        votes_of("yes", "no", "yes", "maybe"),
        synthesis_of("maybe", "Aucun mot-clé LangGraph dans le CV.", "Pas d'agent en prod"),
    )
    got = (await client.get(f"{ROOT}/committee/{second['run_id']}")).json()
    assert got["previous"] == {
        "previous_id": first["run_id"],
        "votes": [
            {"persona": "ats_reader", "before": "no", "after": "yes"},
            {"persona": "recruiter", "before": "no", "after": "no"},
            {"persona": "manager", "before": "maybe", "after": "yes"},
            {"persona": "colleague", "before": "no", "after": "maybe"},
        ],
        "objections_resolved": ["Résultat chiffré enfoui", "Peu d'équipe"],
        "objections_new": ["Pas d'agent en prod"],
    }
    listed = (await client.get(f"{ROOT}/committee", params={"posting_id": posting})).json()
    assert [row["id"] for row in listed] == [second["run_id"], first["run_id"]]
    assert listed[0]["previous"]["previous_id"] == first["run_id"] and listed[1]["previous"] is None


async def test_previous_is_the_last_done_run_of_the_posting(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    """Une exécution en échec n'est jamais « l'avant » : on compare à la dernière terminée."""
    _, version = await ready_committee(client, app)
    first = await launch(client, version)
    await save_done(app, first, votes_of("yes", "yes", "yes", "yes"), synthesis_of("yes"))
    await spy(app).end(str(app.state.local_user_id), first["session_id"])
    failed = await launch(client, version)
    await spy(app).end(str(app.state.local_user_id), failed["session_id"], "failed")
    third = await launch(client, version)
    assert (await run_row(app, third["run_id"])).previous_id == first["run_id"]
