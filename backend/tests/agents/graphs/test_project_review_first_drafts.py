"""Premier appel des brouillons en échec (D173, D165 n° 5) : l'évaluation validée est rangée sans
brouillons, jamais perdue."""

import asyncio

import pytest

from app.agents.nodes.practitioner import drafts as drafts_node
from app.core.errors import AppError
from tests.agents.graphs.project_support import (
    DRAFTS_ASK,
    MakeProject,
    ProjectRun,
    all_met,
    drafts_json,
    project_models,
)
from tests.support.projects import FakeProjectStore


async def _validated_without_drafts(run: ProjectRun, store: FakeProjectStore) -> None:
    """Le premier appel des brouillons a échoué : l'évaluation validée est rangée, sans brouillons
    (D173, D165 n° 5)."""
    await run.wait_status("completed")
    outcome = store.outcome
    assert outcome is not None and outcome.verdict == "validated" and store.review_saves == 1
    assert outcome.drafts == []
    [done] = await run.events("run.completed")
    assert done["summary"] == "Project approved. Drafts unavailable."


async def test_invalid_drafts_keep_the_validated_evaluation_without_drafts(
    project_runner: MakeProject, project_store: FakeProjectStore
) -> None:
    run = await project_runner(project_models(evaluation=[all_met(4)], drafts=["non"] * 3))
    await _validated_without_drafts(run, project_store)


async def test_provider_error_on_the_first_drafts_keeps_the_evaluation(
    project_runner: MakeProject, project_store: FakeProjectStore
) -> None:
    models = project_models(evaluation=[all_met(4)], drafts=[drafts_json()])

    async def fail(agent: str, prompt: str) -> None:
        if DRAFTS_ASK in prompt:
            raise AppError("llm_provider_error", "Panne du fournisseur.", 502)

    models.hooks.append(fail)
    run = await project_runner(models)
    await _validated_without_drafts(run, project_store)


async def test_timeout_on_the_first_drafts_keeps_the_evaluation(
    project_runner: MakeProject,
    project_store: FakeProjectStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(drafts_node, "DRAFTS_BUDGET_S", 0.2)  # son propre délai, ici très court
    models = project_models(evaluation=[all_met(4)], drafts=[drafts_json()])

    async def slow(agent: str, prompt: str) -> None:
        if DRAFTS_ASK in prompt:
            await asyncio.sleep(5)

    models.hooks.append(slow)
    run = await project_runner(models)
    await _validated_without_drafts(run, project_store)
