"""Réponses de formulaire du kit (`form_answers`, D142) : réponse vidée par le code pour une
question salariale ou sans fait du profil, contrôle des faits des réponses."""

from tests.agents.graphs.kit_support import (
    NO_FACT,
    PERMIT,
    SALARY,
    MakeKit,
    answer,
    form,
    prompts,
    writers,
)
from tests.support.kit import FakeKitStore

RETRY_MARKER = "N'écris rien qui ne soit pas dans le profil"


async def test_salary_answer_forced_empty(kit_runner: MakeKit, kit_store: FakeKitStore) -> None:
    run = await kit_runner(writers(form_answers=[form(SALARY, PERMIT)]))
    await run.wait_status("completed")
    row = kit_store.piece("form_answers")
    assert row.status == "to_check" and row.meta["salary"] is True
    assert "For you to fill in" in row.content and "45" not in row.content
    assert [i["state"] for i in row.meta["items"]] == ["salary", "ok"]
    assert len(prompts(run.models, "form_answers")) == 1  # la réponse vidée n'est pas contrôlée


async def test_answer_without_fact_is_emptied(kit_runner: MakeKit, kit_store: FakeKitStore) -> None:
    unknown = answer("Quelle est votre mobilité ?", "Toute la France.", "zz99")
    run = await kit_runner(writers(form_answers=[form(NO_FACT, unknown, PERMIT)]))
    await run.wait_status("completed")
    row = kit_store.piece("form_answers")
    assert row.status == "to_check" and row.meta["salary"] is False
    assert row.content.count("To complete") == 2 and "Immédiate" not in row.content
    assert "Toute la France" not in row.content and "Oui, je conduis" in row.content
    assert [i["state"] for i in row.meta["items"]] == ["to_complete", "to_complete", "ok"]


async def test_form_answer_with_unsupported_claim_retries(
    kit_runner: MakeKit, kit_store: FakeKitStore
) -> None:
    bad = answer("Avez-vous le permis B ?", "Oui, depuis 12 ans.", "x1")
    run = await kit_runner(writers(form_answers=[form(bad), form(PERMIT)]))
    await run.wait_status("completed")
    assert f"{RETRY_MARKER} : 12" in prompts(run.models, "form_answers")[1]
    assert kit_store.piece("form_answers").status == "ready"


async def test_no_eliminatory_question_is_ready_and_empty(
    kit_runner: MakeKit, kit_store: FakeKitStore
) -> None:
    run = await kit_runner(writers(form_answers=[form()]))
    await run.wait_status("completed")
    row = kit_store.piece("form_answers")
    assert row.status == "ready" and "No screening questions" in row.content
