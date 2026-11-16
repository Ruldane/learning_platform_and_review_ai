"""Les projets ne sont jamais journalisés (17.2) : ni la description, ni le lien du dépôt, ni un
critère, ni un brouillon, ni le retour du Praticien, ni le nom d'une capture, ni le titre d'un
projet. Les journaux portent des identifiants, des nombres et des codes."""

import logging

import httpx
import pytest

from app.agents.tools.project_port import DraftResult, ReviewOutcome
from app.agents.tools.project_schema import CriterionResult, ProfileEntryDraft
from app.core.providers import MemoryProviders
from app.features.projects.service.briefs import ensure_project_briefs
from app.features.projects.service.store import AgentProjectStore
from tests.features.projects.support import (
    API,
    NOW,
    PNG,
    WEEK_1,
    Env,
    draft_results,
    shots,
    submit,
)
from tests.features.radar.support import doc
from tests.support.memory import FakeWebReader
from tests.support.projects import sample_brief

SECRETS = (
    "SECRET-DESCRIPTION",
    "secret-lien",
    "secret-nom-capture",
    "SECRET-CRITERE",
    "SECRET-RETOUR",
    "SECRET-COMMENTAIRE",
    "SECRET-BROUILLON",
    "SECRET-TITRE",
    "SECRET-ENTREE",
    "SECRET-README",
)
LINK = "https://example.org/secret-lien/depot"
DESCRIPTION = "SECRET-DESCRIPTION de mon travail"


def secret_drafts() -> list[DraftResult]:
    return [
        DraftResult(
            kind=d.kind,
            content="SECRET-BROUILLON " + d.content,
            entry=ProfileEntryDraft(name="SECRET-ENTREE") if d.entry else None,
            status=d.status,
            flags=d.flags,
        )
        for d in draft_results()
    ]


async def refused_and_unreadable(env: Env, client: httpx.AsyncClient, pid: str) -> None:
    """Un lien refusé (422), une fausse image, un dépôt inconnu et un lien invalide : codes."""
    bad_link = {"repo_url": "ftp://secret-lien/x", "description": DESCRIPTION}
    assert (await submit(client, pid, data=bad_link)).status_code == 422
    fake = shots(("secret-nom-capture.png", PNG), ("secret-nom-capture.txt", b"faux"))
    assert (
        await submit(client, pid, data={"description": DESCRIPTION}, files=fake)
    ).status_code == 422
    store = AgentProjectStore(env.rt)
    assert (
        await store.repo_text(env.user_id, "s1", "https://example.org/secret-lien/inconnu") is None
    )
    assert await store.repo_text(env.user_id, "s1", "pas-un-lien-secret-lien") is None


async def review_and_edit(env: Env, client: httpx.AsyncClient, pid: str) -> None:
    """Un rendu valable, son évaluation (rejouée), des brouillons retouchés, l'entrée au profil."""
    data = {"repo_url": LINK, "description": DESCRIPTION}
    sent = await submit(client, pid, data=data, files=shots(("secret-nom-capture.png", PNG)))
    assert sent.status_code == 202
    session_id = sent.json()["session_id"]
    store = AgentProjectStore(env.rt)
    assert await store.repo_text(env.user_id, session_id, LINK) is not None
    results = [CriterionResult(index=n, met=True, comment="SECRET-COMMENTAIRE") for n in (1, 2, 3)]
    issue = ReviewOutcome("validated", results, "SECRET-RETOUR", "read", secret_drafts())
    await store.save_review(env.user_id, session_id, pid, issue)
    await store.save_review(env.user_id, session_id, pid, issue)  # le rejeu
    await client.patch(f"{API}/{pid}/drafts/cv_line", json={"content": "SECRET-BROUILLON bis"})
    await client.patch(f"{API}/{pid}/drafts/readme_plan", json={"content": "SECRET-BROUILLON"})
    for _ in range(2):  # le second clic est refusé (409)
        await client.post(f"{API}/{pid}/profile-entry", json={"name": "SECRET-ENTREE"})


async def test_projects_never_logged(
    env: Env,
    client: httpx.AsyncClient,
    caplog: pytest.LogCaptureFixture,
    memory_providers: MemoryProviders,
) -> None:
    caplog.set_level(logging.DEBUG, logger="app")
    brief = sample_brief(title="SECRET-TITRE du projet").model_dump(mode="json")
    brief["criteria"] = ["SECRET-CRITERE un", "SECRET-CRITERE deux", "SECRET-CRITERE trois"]
    await env.add_profile(2)
    pid = await env.add_project(brief=brief, title="SECRET-TITRE du projet")
    web = memory_providers.web
    assert isinstance(web, FakeWebReader)
    web.pages[LINK] = doc(LINK, "SECRET-README du dépôt")
    await refused_and_unreadable(env, client, pid)
    await review_and_edit(env, client, pid)
    assert (await client.get(f"{API}/{pid}")).status_code == 200
    assert (await client.get(API)).status_code == 200
    assert (await client.get(f"{API}/{pid}/screenshots/1")).status_code == 200
    for moment in (WEEK_1, NOW):
        env.at(moment)
        await ensure_project_briefs(env.rt, moment)
    text = "\n".join(record.getMessage() for record in caplog.records)
    assert "Évaluation rangée" in text  # les journaux existent : ils ne disent que les nombres
    for secret in SECRETS:
        assert secret.lower() not in text.lower(), secret
    assert "example.org" not in text
