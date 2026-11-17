"""Parcours `project_review` : rejeu après un arrêt (l'évaluation rangée n'est pas redemandée,
l'issue n'est rangée qu'une fois), journaux sans texte du projet, et branchement du parcours."""

import logging

import pytest

from app.agents.graphs.project_review import ProjectReviewInput
from app.agents.graphs.registry import get_graph
from tests.agents.graphs.council_models import CouncilModels
from tests.agents.graphs.project_support import (
    DRAFTS_ASK,
    EVALUATE_ASK,
    SECRET_POST,
    MakeProject,
    all_met,
    drafts_json,
    project_models,
    prompts,
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
    assert ProjectReviewInput(project_id=PROJECT_ID).model_dump() == {
        "project_id": PROJECT_ID,
        "mode": "review",
    }
    with pytest.raises(ValueError):
        ProjectReviewInput(project_id="court")
    assert len(sample_brief().criteria) == 4


RETRY_MARK = "Ces éléments ne figurent"


def _blocked_models(first_jet: str) -> CouncilModels:
    """Faux modèles dont le nouvel essai des brouillons reste bloqué (l'arrêt du processus)."""
    models = project_models(evaluation=[all_met(4)], drafts=[first_jet, first_jet])
    models.block = lambda agent, prompt: RETRY_MARK in prompt
    return models


async def test_redo_resume_after_restart(
    project_runner: MakeProject, project_store: FakeProjectStore
) -> None:
    """Arrêt pendant le nouvel essai des brouillons (`redo`) : au redémarrage, ni l'évaluation ni
    le premier jet ne sont redemandés ; le nouvel essai reprend sur le premier jet du point de
    contrôle (les termes qu'il nomme) et l'issue n'est rangée qu'une fois."""
    first_models = _blocked_models(drafts_json(linkedin_post=SECRET_POST))
    first = await project_runner(first_models)
    await wait_until(lambda: first_models.blocked == 1)
    await first.runner.shutdown()
    assert project_store.review_saves == 0  # rien n'est rangé avant la fin du nouvel essai

    fixed = project_models(drafts=[drafts_json()])
    second = await project_runner(fixed, sid=first.sid)
    assert await second.runner.recover_on_startup() == [first.sid]
    await second.wait_status("completed")
    assert second.calls(EVALUATE_ASK) == 0  # l'évaluation n'est pas redemandée
    [retry] = prompts(fixed, DRAFTS_ASK)  # un seul appel : le nouvel essai, pas le premier jet
    assert RETRY_MARK in retry and "Kubernetes" in retry  # sur le premier jet du point de contrôle
    outcome = project_store.outcome
    assert project_store.review_saves == 1 and outcome is not None and outcome.drafts is not None
    assert {d.status for d in outcome.drafts} == {"ready"}
    [done] = await second.events("run.completed")
    assert done["summary"] == "Projet validé : 4 brouillons prêts."


async def test_redo_with_nothing_left_to_fix_makes_no_call(
    project_runner: MakeProject, project_store: FakeProjectStore
) -> None:
    """À la reprise, le premier jet n'a plus rien à corriger (le rendu de January a changé depuis
    l'arrêt) : aucun message vide au modèle, le premier jet est rangé propre."""
    first_models = _blocked_models(drafts_json(linkedin_post=SECRET_POST))
    first = await project_runner(first_models)
    await wait_until(lambda: first_models.blocked == 1)
    await first.runner.shutdown()

    said = f"{DESCRIPTION} J'ai eu 10000 utilisateurs et un déploiement sur Kubernetes."
    project_store.review = review_inputs(description=said)
    unused = project_models(drafts=[drafts_json()])
    second = await project_runner(unused, sid=first.sid)
    assert await second.runner.recover_on_startup() == [first.sid]
    await second.wait_status("completed")
    assert second.calls(DRAFTS_ASK) == 0  # aucun nouvel essai
    outcome = project_store.outcome
    assert outcome is not None and outcome.drafts is not None
    assert {d.status for d in outcome.drafts} == {"ready"} and not any(
        d.flags for d in outcome.drafts
    )
    assert "Kubernetes" in {d.kind: d for d in outcome.drafts}["linkedin_post"].content
