"""Parcours `application_intake` (D141) : une phrase de January devient une fiche en préparation,
confirmée par `interrupt()` (avec l'alerte de doublon), puis créée par le port. Le nœud de la
question est seul et pur, la création est idempotente (Review Focus n° 1 et n° 4)."""

from datetime import date
from typing import Any

import pytest

from app.agents.graphs.application_intake import ApplicationIntakeInput
from app.agents.graphs.registry import get_graph
from app.agents.registry import AGENTS
from app.features.sessions.service import ROUTE_ONLY
from tests.agents.graphs.intake_support import (
    SENTENCE,
    MakeIntake,
    draft_json,
    field_values,
    tracker,
    tracker_prompts,
)
from tests.agents.graphs.review_support import in_untrusted
from tests.support.applications import (
    ALERT_MESSAGE,
    EXISTING_ID,
    OTHER_EXISTING_ID,
    FakeApplicationStore,
    alert,
)

MISSING = "Je n'ai pas trouvé l'entreprise ou le poste dans ta phrase."


async def test_sentence_becomes_confirmed_application(
    intake_runner: MakeIntake, intake_store: FakeApplicationStore
) -> None:
    run = await intake_runner()
    question = await run.question()
    assert question["question"] == "Je crée cette fiche ?"
    assert [o["value"] for o in question["options"]] == ["create", "cancel"]
    values = field_values(question)
    assert values["applied_on"] == "2026-11-14" and values["status"] == "applied"
    assert (values["company"], values["title"]) == ("Société Fictive", "Développeuse IA")
    assert intake_store.saved == []  # rien n'est écrit avant la confirmation
    await run.answer({"choice": "create", "fields": values})
    await run.wait_status("completed")
    assert intake_store.saved == [
        ("Société Fictive", "Développeuse IA", "applied", date(2026, 11, 14))
    ]
    application_id = intake_store.created[run.sid]
    [artifact] = await run.events("artifact.ready")
    assert artifact == {
        "artifact_id": application_id,
        "kind": "application",
        "title": "Candidature chez Société Fictive",
        "url": f"/candidatures/{application_id}",
    }


async def test_prompt_gives_today_and_weekdays(intake_runner: MakeIntake) -> None:
    run = await intake_runner()
    await run.question()
    [prompt] = tracker_prompts(run.models)
    assert "dimanche 15 novembre 2026" in prompt and "(2026-11-15)" in prompt
    assert "hier : samedi 14 novembre 2026 (2026-11-14)" in prompt
    assert "lundi 9 novembre 2026 (2026-11-09)" in prompt


async def test_intake_duplicate_shows_alert_in_question(
    intake_runner: MakeIntake, intake_store: FakeApplicationStore
) -> None:
    intake_store.alerts = [alert(), alert(OTHER_EXISTING_ID, "possible")]
    run = await intake_runner()
    question = await run.question()
    assert question["question"] == f"Je crée cette fiche ? {ALERT_MESSAGE}"
    assert [o["value"] for o in question["options"]] == ["distinct", "open", "cancel"]
    labels = {o["value"]: o["label"] for o in question["options"]}
    assert labels["distinct"] == "C'est un autre poste"
    assert labels["open"] == "Ouvrir la fiche existante"
    assert intake_store.alert_calls[0].company == "Société Fictive"


async def test_intake_distinct_creates_with_distinct_from(
    intake_runner: MakeIntake, intake_store: FakeApplicationStore
) -> None:
    intake_store.alerts = [alert(), alert(OTHER_EXISTING_ID, "possible")]
    run = await intake_runner()
    await run.question()
    await run.answer({"choice": "distinct"})
    await run.wait_status("completed")
    assert intake_store.distinct_calls == [[EXISTING_ID, OTHER_EXISTING_ID]]
    assert len(intake_store.drafts) == 1


async def test_intake_open_returns_the_existing_application(
    intake_runner: MakeIntake, intake_store: FakeApplicationStore
) -> None:
    intake_store.alerts = [alert(), alert(OTHER_EXISTING_ID, "possible")]
    run = await intake_runner()
    await run.question()
    await run.answer("open")
    await run.wait_status("completed")
    assert intake_store.save_calls == 0
    [artifact] = await run.events("artifact.ready")
    assert artifact["artifact_id"] == EXISTING_ID and artifact["kind"] == "application"
    assert artifact["url"] == f"/candidatures/{EXISTING_ID}"


async def test_intake_cancel_saves_nothing(
    intake_runner: MakeIntake, intake_store: FakeApplicationStore
) -> None:
    run = await intake_runner()
    await run.question()
    await run.answer({"choice": "cancel"})
    await run.wait_status("completed")
    [done] = await run.events("run.completed")
    assert done["summary"] == "Rien n'a été créé."
    assert intake_store.save_calls == 0 and await run.events("artifact.ready") == []


async def test_future_date_is_asked_again(intake_runner: MakeIntake) -> None:
    run = await intake_runner(tracker(draft_json(applied_on="2026-11-20")))
    question = await run.question()
    assert field_values(question)["applied_on"] == "2026-11-14"
    first, second = tracker_prompts(run.models)
    assert "futur" not in first and "dans le futur" in second  # le refus est renvoyé au modèle
    assert "2026-11-20" not in second.split("Ta réponse précédente")[1].split("\n")[1]


@pytest.mark.parametrize(
    "missing", [{"company": ""}, {"title": ""}, {"company": "  ", "title": ""}]
)
async def test_missing_company_or_title_fails_cleanly(
    intake_runner: MakeIntake, intake_store: FakeApplicationStore, missing: dict[str, Any]
) -> None:
    run = await intake_runner(tracker(draft_json(**missing)))
    row = await run.wait_status("failed")
    assert row.error is not None
    assert (row.error["code"], row.error["message"]) == ("intake_incomplete", MISSING)
    assert intake_store.alert_calls == [] and intake_store.save_calls == 0


async def test_invented_company_is_asked_again(intake_runner: MakeIntake) -> None:
    run = await intake_runner(tracker(draft_json(company="Autre SA")))
    question = await run.question()
    assert field_values(question)["company"] == "Société Fictive"
    assert len(tracker_prompts(run.models)) == 2


async def test_unreadable_sentence_fails_with_a_readable_message(
    intake_runner: MakeIntake,
) -> None:
    run = await intake_runner(tracker("pas du json", "toujours pas", "encore pas"))
    row = await run.wait_status("failed")
    assert row.error is not None and row.error["code"] == "intake_unreadable"
    assert "reformule" in row.error["message"]


async def test_sentence_is_untrusted(intake_runner: MakeIntake) -> None:
    run = await intake_runner()
    await run.question()
    [prompt] = tracker_prompts(run.models)
    assert SENTENCE in prompt and in_untrusted(prompt, SENTENCE)
    assert 'source="phrase de January"' in prompt


def test_graph_is_registered_with_its_own_route() -> None:
    spec = get_graph("application_intake")
    assert spec.input_model is ApplicationIntakeInput
    assert ROUTE_ONLY["application_intake"] == "POST /applications/intake"
    assert AGENTS["tracker"].tier == "rapide"
    for text in ("", "x" * 1001):
        with pytest.raises(ValueError):
            ApplicationIntakeInput.model_validate({"text": text})
    assert ApplicationIntakeInput(text=SENTENCE).model_dump() == {"text": SENTENCE}
