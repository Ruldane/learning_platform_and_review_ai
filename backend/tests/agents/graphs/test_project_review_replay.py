"""Parcours `project_review` : rejeu après un arrêt (l'évaluation rangée n'est pas redemandée,
l'issue n'est rangée qu'une fois), journaux sans texte du projet, et branchement du parcours."""

import logging

import pytest

from app.agents.graphs.project_review import ProjectReviewInput
from app.agents.graphs.registry import get_graph
from tests.agents.graphs.project_support import (
    DRAFTS_ASK,
    EVALUATE_ASK,
    SECRET_POST,
    MakeProject,
    all_met,
    drafts_json,
    project_models,
)
from tests.agents.runtime.runner_helpers import wait_until
from tests.support.projects import (
    CRITERIA,
    DESCRIPTION,
    PROJECT_ID,
    README,
    REPO_URL,
    TITLE,
    FakeProjectStore,
    review_inputs,
    sample_brief,
)


async def test_replay_saves_review_once(
    project_runner: MakeProject, project_store: FakeProjectStore
) -> None:
    first_models = project_models(evaluation=[all_met(4)], drafts=[drafts_json()])
    first_models.block = lambda agent, prompt: DRAFTS_ASK in prompt  # arrêt avant les brouillons
    first = await project_runner(first_models)
    await wait_until(lambda: first_models.blocked == 1)
    await first.runner.shutdown()
    second_models = project_models(evaluation=[all_met(4)], drafts=[drafts_json()])
    second = await project_runner(second_models, sid=first.sid)
    assert await second.runner.recover_on_startup() == [first.sid]
    await second.wait_status("completed")
    assert first.calls(EVALUATE_ASK) == 1 and second.calls(EVALUATE_ASK) == 0  # pas de 2e appel
    assert second.calls(DRAFTS_ASK) == 1  # les brouillons reprennent là où ils s'étaient arrêtés
    assert project_store.review_saves == 1 and project_store.repo_calls == [REPO_URL]
    assert project_store.outcome is not None and project_store.outcome.verdict == "validated"
    [done] = await second.events("run.completed")
    assert done["summary"] == "Projet validé : 4 brouillons prêts."


async def test_project_texts_never_logged(
    caplog: pytest.LogCaptureFixture, project_runner: MakeProject, project_store: FakeProjectStore
) -> None:
    caplog.set_level(logging.DEBUG, logger="app")  # nos journaux ; le reste (SQL) n'est pas à nous
    project_store.repo_error = RuntimeError("Panne secrète du lecteur")
    drafts = drafts_json(linkedin_post=SECRET_POST)
    models = project_models(evaluation=[all_met(4)], drafts=[drafts, drafts])
    run = await project_runner(models)
    await run.wait_status("completed")
    logged = "\n".join(r.getMessage() for r in caplog.records if r.name.startswith("app"))
    assert "Rendu lu" in logged and "Évaluation rangée" in logged and "RuntimeError" in logged
    secrets = [TITLE, DESCRIPTION, README, REPO_URL, "example.org", "Panne secrète", "Kubernetes"]
    secrets += [*CRITERIA, "10000", "10 000", "Conçu une API", "Présentation", "Un rendu clair"]
    secrets += [EVALUATE_ASK, DRAFTS_ASK, "FastAPI", "Camille"]
    for secret in secrets:
        assert secret not in logged


async def test_failed_review_logs_only_a_code(
    caplog: pytest.LogCaptureFixture, project_runner: MakeProject, project_store: FakeProjectStore
) -> None:
    caplog.set_level(logging.DEBUG, logger="app")
    project_store.review = review_inputs(description="Mon texte secret de rendu.")
    run = await project_runner(project_models(evaluation=["pas du JSON secret"] * 3))
    await run.wait_status("failed")
    logged = "\n".join(r.getMessage() for r in caplog.records if r.name.startswith("app"))
    assert "Mon texte secret" not in logged and "pas du JSON secret" not in logged


def test_graph_is_registered() -> None:
    spec = get_graph("project_review")
    assert spec.input_model is ProjectReviewInput and spec.recursion_limit is None
    assert ProjectReviewInput(project_id=PROJECT_ID).model_dump() == {"project_id": PROJECT_ID}
    with pytest.raises(ValueError):
        ProjectReviewInput(project_id="court")
    assert len(sample_brief().criteria) == 4
