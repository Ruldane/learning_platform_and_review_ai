"""La source `project` du fil d'activité (rule 6, 8.10) : « Projet validé : {titre} » et « Projet à
reprendre : {titre} » avec le lien du Portfolio, instants de la dernière évaluation, identifiants
stables, aucun texte du rendu, curseur `(at, id)` et isolation par utilisatrice."""

import logging
from datetime import datetime

import pytest

from app.db.models.daily import Project
from tests.features.activity.support import OTHER, Env, add_user, hours
from tests.features.activity.support import page as _page


async def add_project(
    env: Env,
    at: datetime,
    *,
    status: str = "validated",
    title: str = "Une API de suivi",
    module: str = "m1",
    attempts: int = 1,
    user: str | None = None,
    verdict: str | None = None,
) -> str:
    """Un projet dont la dernière évaluation date de `at` (`status` : son statut, `verdict` : celui
    de son évaluation, le même par défaut)."""
    async with env.factory() as db:
        row = Project(
            user_id=user or env.user_id,
            module_id=module,
            program_id="p1",
            title=title,
            status=status,
            submissions=[{"description": "Description secrète"}] * attempts,
            evaluation={
                "session_id": f"s-{at.isoformat()}",
                "at": at.isoformat(),
                "verdict": verdict or status,
                "results": [],
                "feedback": "Retour secret",
                "repo_status": "read",
            },
            validated_at=at if status == "validated" else None,
        )
        db.add(row)
        await db.commit()
        return row.id


async def test_validated_and_to_redo_projects_are_in_the_feed(env: Env) -> None:
    done = await add_project(env, hours(2))
    redo = await add_project(
        env, hours(3), status="to_redo", title="Un tableau de bord", module="m2"
    )
    page = await _page(env)
    assert [item.kind for item in page.items] == ["project", "project"]
    redo_item, done_item = page.items
    assert redo_item.title == "Project needs revision: Un tableau de bord"
    assert redo_item.link == f"/skills/portfolio/{redo}" and redo_item.at == hours(3)
    assert (
        redo_item.id == f"project:{redo}:to_redo:s-{hours(3).isoformat()}"
        and redo_item.detail is None
    )
    assert done_item.title == "Project approved: Une API de suivi"
    assert done_item.link == f"/skills/portfolio/{done}" and done_item.at == hours(2)
    assert done_item.id == f"project:{done}:validated"
    dumped = page.model_dump_json()
    assert "secret" not in dumped  # ni la description, ni le retour du Praticien


async def test_a_project_being_reviewed_again_is_not_an_event(env: Env) -> None:
    await add_project(env, hours(1), status="reviewing", verdict="to_redo")
    await add_project(env, hours(2), status="todo", verdict="to_redo", module="m2")
    await add_project(env, hours(3), status="brief_pending", module="m3")
    assert (await _page(env)).items == []


async def test_a_second_evaluation_to_redo_is_a_new_event(env: Env) -> None:
    pid = await add_project(env, hours(1), status="to_redo", attempts=1)
    first = (await _page(env)).items[0].id
    async with env.factory() as db:
        row = await db.get(Project, pid)
        assert row is not None
        row.submissions = [*row.submissions, {}]
        row.evaluation = {**(row.evaluation or {}), "at": hours(5).isoformat(), "session_id": "s2"}
        await db.commit()
    second = (await _page(env)).items[0]
    assert second.id != first and second.at == hours(5)


async def test_a_new_submission_that_dies_does_not_change_the_event(env: Env) -> None:
    """Un rendu de plus dont la session meurt (le statut redevient `to_redo`, l'évaluation est
    inchangée) ne change ni l'identifiant ni l'instant : le curseur `(at, id)` ne le revoit pas."""
    pid = await add_project(env, hours(1), status="to_redo", attempts=1)
    first = (await _page(env)).items[0]
    async with env.factory() as db:
        row = await db.get(Project, pid)
        assert row is not None
        row.submissions = [*row.submissions, {}]  # un rendu de plus, évaluation inchangée
        await db.commit()
    again = (await _page(env)).items[0]
    assert (again.id, again.at) == (first.id, first.at)
    newer = await _page(env, after=first.at, after_id=first.id)
    assert newer.items == []


async def test_after_and_before_cursors_on_projects(env: Env) -> None:
    ids = [await add_project(env, hours(n), module=f"m{n}") for n in (1, 2, 3)]
    newer = await _page(env, after=hours(1))
    assert [item.at for item in newer.items] == [hours(3), hours(2)]
    older = await _page(env, before=hours(3), before_id=f"project:{ids[2]}:validated")
    assert [item.at for item in older.items] == [hours(2), hours(1)]
    window = await _page(env, after=hours(1), before=hours(3))
    assert [item.at for item in window.items] == [hours(2)]


async def test_project_events_are_per_user(env: Env) -> None:
    await add_user(env)
    await add_project(env, hours(1))
    await add_project(env, hours(2), user=OTHER, title="Celui de l'autre")
    mine = await _page(env)
    theirs = await _page(env, user=OTHER)
    assert [item.title for item in mine.items] == ["Project approved: Une API de suivi"]
    assert [item.title for item in theirs.items] == ["Project approved: Celui de l'autre"]


async def test_project_source_never_logs_texts(env: Env, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG, logger="app")
    await add_project(env, hours(1), title="Titre secret du projet")
    assert (await _page(env)).items
    text = "\n".join(record.getMessage() for record in caplog.records)
    assert "secret" not in text.lower()
