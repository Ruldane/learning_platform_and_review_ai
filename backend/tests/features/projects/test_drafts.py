"""Retoucher un brouillon (rule 4, D166) : `edited`, un brouillon « à vérifier » recontrôlé par
`text_claims` contre la référence du Praticien (profil validé, ce que January dit du projet,
compétences du module), longueur du post LinkedIn, 422 sans écho, jamais d'écriture au profil."""

from typing import Any

import httpx
import pytest

from app.features.projects.service.store import AgentProjectStore
from tests.features.projects.support import API, CLEAN_POST, Env, draft_results, outcome

CHECK = ["cv_line", "linkedin_post", "readme_plan"]


@pytest.fixture
async def pid(env: Env) -> str:
    """Un projet validé dont trois brouillons sont « à vérifier » (terme « kubernetes »)."""
    project_id = await env.add_project(status="reviewing", submissions=[env.last_submission()])
    await env.add_profile(2)
    await AgentProjectStore(env.rt).save_review(
        env.user_id, "s1", project_id, outcome(drafts=draft_results(to_check=CHECK))
    )
    return project_id


def draft(body: dict[str, Any], kind: str) -> dict[str, Any]:
    found: dict[str, Any] = next(item for item in body["drafts"] if item["kind"] == kind)
    return found


async def patch(client: httpx.AsyncClient, pid: str, kind: str, **body: Any) -> httpx.Response:
    return await client.patch(f"{API}/{pid}/drafts/{kind}", json=body)


async def test_patch_marks_edited_and_a_ready_draft_stays_ready(
    pid: str, client: httpx.AsyncClient
) -> None:
    r = await patch(
        client,
        pid,
        "profile_entry",
        entry={"name": "Mon projet", "description": "Une API", "achievements": ["Trois routes"]},
    )
    assert r.status_code == 200
    entry = draft(r.json(), "profile_entry")
    assert (entry["status"], entry["edited"], entry["flags"]) == ("ready", True, [])
    assert entry["content"] == "Mon projet\nUne API\nTrois routes"
    assert entry["entry"] == {
        "name": "Mon projet",
        "description": "Une API",
        "achievements": ["Trois routes"],
    }
    untouched = draft(r.json(), "cv_line")
    assert untouched["edited"] is False and untouched["status"] == "to_check"


async def test_patch_to_check_draft_rechecked(pid: str, client: httpx.AsyncClient) -> None:
    # dit ce que January a dit : plus rien à vérifier
    clean = await patch(
        client, pid, "cv_line", content="Construit une API de suivi de lecture avec FastAPI."
    )
    cv = draft(clean.json(), "cv_line")
    assert (cv["status"], cv["flags"], cv["edited"]) == ("ready", [], True)
    # un terme que ni le profil ni le projet ne disent : à vérifier, nommé
    bad = await patch(
        client, pid, "readme_plan", content="Installation\nDéploiement sur Kubernetes"
    )
    plan = draft(bad.json(), "readme_plan")
    assert plan["status"] == "to_check" and plan["edited"] is True
    assert [flag.lower() for flag in plan["flags"]] == ["kubernetes"]
    fixed = await patch(client, pid, "readme_plan", content="Installation\nUtilisation\nTests")
    assert draft(fixed.json(), "readme_plan")["status"] == "ready"


async def test_the_linkedin_post_is_rechecked_for_terms_and_length(
    pid: str, client: httpx.AsyncClient
) -> None:
    short = await patch(client, pid, "linkedin_post", content="Un post bien trop court.")
    post = draft(short.json(), "linkedin_post")
    assert post["status"] == "to_check" and post["flags"] == ["5 mots (80 à 200 attendus)"]
    both = await patch(
        client, pid, "linkedin_post", content=CLEAN_POST + " Déployé sur Kubernetes."
    )
    flags = draft(both.json(), "linkedin_post")["flags"]
    assert [flag.lower() for flag in flags] == ["kubernetes"]
    ok = await patch(client, pid, "linkedin_post", content=CLEAN_POST)
    post = draft(ok.json(), "linkedin_post")
    assert (post["status"], post["flags"], post["content"]) == ("ready", [], CLEAN_POST)


async def test_a_ready_draft_edited_stays_ready_even_with_new_words(
    env: Env, client: httpx.AsyncClient
) -> None:
    project_id = await env.add_project(status="reviewing", submissions=[env.last_submission()])
    await AgentProjectStore(env.rt).save_review(env.user_id, "s1", project_id, outcome())
    r = await patch(client, project_id, "cv_line", content="Mes mots à moi, avec Kubernetes.")
    cv = draft(r.json(), "cv_line")
    assert (cv["status"], cv["flags"], cv["edited"]) == ("ready", [], True)


async def test_patch_needs_the_field_of_the_kind(pid: str, client: httpx.AsyncClient) -> None:
    for kind, body, field in [
        ("profile_entry", {"content": "Texte secret"}, "entry"),
        ("cv_line", {"entry": {"name": "Nom secret"}}, "entry"),
        ("cv_line", {}, "content"),
        ("cv_line", {"content": "   "}, "content"),
        ("profile_entry", {}, "entry"),
    ]:
        r = await patch(client, pid, kind, **body)
        assert r.status_code == 422, (kind, body)
        assert r.json()["error"]["details"] == {"fields": [field]}
        assert "secret" not in r.text.lower()


async def test_patch_validates_sizes_without_echo(pid: str, client: httpx.AsyncClient) -> None:
    r = await patch(
        client, pid, "cv_line", content="texte-secret " * 300
    )  # plus de 3 000 caractères
    assert r.status_code == 422 and r.json()["error"]["details"] == {"fields": ["content"]}
    assert "texte-secret" not in r.text
    r = await patch(client, pid, "profile_entry", entry={"name": "", "description": "secrète"})
    assert r.status_code == 422 and r.json()["error"]["details"] == {"fields": ["entry.name"]}
    r = await patch(
        client, pid, "profile_entry", entry={"name": "Un nom", "achievements": ["a"] * 5}
    )
    assert r.status_code == 422 and r.json()["error"]["details"] == {
        "fields": ["entry.achievements"]
    }


async def test_patch_unknown_kind_and_missing_draft(env: Env, client: httpx.AsyncClient) -> None:
    project_id = await env.add_project()  # pas de brouillon avant la validation
    missing = await patch(client, project_id, "cv_line", content="Un texte")
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "draft_not_found"
    unknown = await patch(client, project_id, "tweet", content="Un texte")
    assert unknown.status_code == 422 and unknown.json()["error"]["details"] == {"fields": ["kind"]}
    absent = await patch(client, "inconnu", "cv_line", content="Un texte")
    assert absent.status_code == 404 and absent.json()["error"]["code"] == "project_not_found"


async def test_patch_never_touches_the_master_profile(
    env: Env, pid: str, client: httpx.AsyncClient
) -> None:
    before = await env.profile_versions()
    await patch(client, pid, "profile_entry", entry={"name": "Mon projet"})
    after = await env.profile_versions()
    assert [v.version for v in after] == [v.version for v in before] == [1, 2]
    assert all(not v.data["projects"] for v in after)
