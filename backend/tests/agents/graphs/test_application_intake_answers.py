"""Parcours `application_intake` (D141), la confirmation : champs corrigés, réponses invalides,
doublon qui bloque `create`, nœud de la question sans écriture, rejeu après un arrêt du back
(Review Focus n° 4), journaux sans la phrase."""

import inspect
import logging
from datetime import date

import pytest

from app.agents.nodes.tracker.confirm import ask_confirm
from app.core.errors import AppError
from tests.agents.graphs.intake_support import MakeIntake, draft_json, field_values, tracker
from tests.agents.runtime.runner_helpers import wait_until
from tests.support.applications import FakeApplicationStore, alert


async def test_edited_fields_are_saved(
    intake_runner: MakeIntake, intake_store: FakeApplicationStore
) -> None:
    run = await intake_runner()
    values = field_values(await run.question())
    values |= {
        "company": "Autre SA",
        "status": "interview",
        "applied_on": "2026-11-10",
        "channel": "linkedin",
        "contact_name": "Camille Exemple",
        "contact_role": "Recruteuse",
        "notes": "Échange par message.",
    }
    await run.answer({"choice": "create", "fields": values})
    await run.wait_status("completed")
    [draft] = intake_store.drafts
    assert (draft.company, draft.status, draft.applied_on, draft.channel) == (
        "Autre SA",
        "interview",
        date(2026, 11, 10),
        "linkedin",
    )
    assert (draft.contact_name, draft.contact_role, draft.notes) == (
        "Camille Exemple",
        "Recruteuse",
        "Échange par message.",
    )


async def test_invalid_answers_ask_again_without_writing(
    intake_runner: MakeIntake, intake_store: FakeApplicationStore
) -> None:
    run = await intake_runner()
    first = await run.question()
    values = field_values(first)
    calls = len(run.models.calls)
    for bad in (
        "oui",
        {"choice": "autre"},
        {"choice": "distinct"},  # sans alerte : rien à confirmer
        {"choice": "open"},
        {"choice": "create", "fields": values | {"applied_on": "2026-11-16"}},  # dans le futur
        {"choice": "create", "fields": values | {"applied_on": "hier"}},
        {"choice": "create", "fields": values | {"company": ""}},
        {"choice": "create", "fields": values | {"status": "inconnu"}},
        {"choice": "create", "fields": {"channel": 3}},
    ):
        await run.answer(bad)
        again = await run.question()
        assert (
            again["interrupt_id"] != first["interrupt_id"]
            and again["kind"] == "application_confirm"
        )
        assert again["fields"] == first["fields"] and again["question"] == first["question"]
        first = again
    assert intake_store.save_calls == 0 and len(run.models.calls) == calls


async def test_create_is_refused_while_an_alert_stands(
    intake_runner: MakeIntake, intake_store: FakeApplicationStore
) -> None:
    """Même règle que la route : une fiche qui ressemble ne se crée pas sans « autre poste »."""
    intake_store.alerts = [alert()]
    run = await intake_runner()
    first = await run.question()
    await run.answer({"choice": "create", "fields": field_values(first)})
    again = await run.question()
    assert again["interrupt_id"] != first["interrupt_id"] and intake_store.save_calls == 0


async def test_interrupt_node_has_no_write(
    intake_runner: MakeIntake, intake_store: FakeApplicationStore
) -> None:
    assert list(inspect.signature(ask_confirm).parameters) == ["state"]  # ni port ni modèle
    run = await intake_runner()
    await run.question()
    assert intake_store.context_calls == 1 and len(intake_store.alert_calls) == 1
    await run.answer({"choice": "cancel"})
    await run.wait_status("completed")
    assert intake_store.context_calls == 1 and len(intake_store.alert_calls) == 1


async def test_replay_at_question_keeps_question(
    intake_runner: MakeIntake, intake_store: FakeApplicationStore
) -> None:
    """Le back redémarre pendant que la question attend : la même question attend, rien n'est
    relu ni écrit deux fois, et la réponse est reçue par le nouveau processus."""
    first = await intake_runner()
    question = await first.question()
    await first.runner.shutdown()
    second = await intake_runner(tracker(), sid=first.sid)
    assert await second.runner.recover_on_startup() == []  # `waiting_user` : rien à relancer
    row = await second.wait_status("waiting_user")
    assert row.pending_interrupt is not None
    assert row.pending_interrupt["interrupt_id"] == question["interrupt_id"]
    assert row.pending_interrupt["kind"] == "application_confirm"
    assert intake_store.save_calls == 0 and second.models.calls == []
    assert intake_store.context_calls == 1
    await second.answer({"choice": "create", "fields": field_values(question)})
    await second.wait_status("completed")
    assert len(intake_store.drafts) == 1


async def test_save_is_idempotent(
    intake_runner: MakeIntake, intake_store: FakeApplicationStore
) -> None:
    """Arrêt du back pendant la création : le nœud rejoué relit la fiche de la session."""
    intake_store.block_after_save = True
    first = await intake_runner()
    question = await first.question()
    await first.answer({"choice": "create", "fields": field_values(question)})
    await wait_until(lambda: intake_store.save_calls == 1)
    await first.runner.shutdown()
    intake_store.block_after_save = False
    second = await intake_runner(tracker(), sid=first.sid)
    assert await second.runner.recover_on_startup() == [first.sid]
    await second.wait_status("completed")
    assert intake_store.save_calls == 2 and len(intake_store.created) == 1
    assert len(intake_store.drafts) == 1 and second.models.calls == []
    [artifact] = await second.events("artifact.ready")
    assert artifact["artifact_id"] == intake_store.created[first.sid]


async def test_store_refusal_fails_with_its_message(
    intake_runner: MakeIntake, intake_store: FakeApplicationStore
) -> None:
    intake_store.refuse_with = AppError(
        "application_duplicate", "Cette offre ressemble à une candidature existante.", 409
    )
    run = await intake_runner()
    await run.answer({"choice": "create", "fields": field_values(await run.question())})
    row = await run.wait_status("failed")
    assert row.error is not None and row.error["code"] == "application_duplicate"


async def test_intake_text_never_logged(
    caplog: pytest.LogCaptureFixture,
    intake_runner: MakeIntake,
    intake_store: FakeApplicationStore,
) -> None:
    caplog.set_level(logging.INFO)  # pas le SQL d'aiosqlite, qui cite la ligne de la session
    caplog.set_level(logging.DEBUG, logger="app")
    secrets = ("Entreprise Ultra Secrète", "Intitulé Ultra Secret", "Contact Ultra Secret")
    text = f"j'ai postulé hier chez {secrets[0]} pour {secrets[1]}, contact {secrets[2]}"
    reply = draft_json(
        company=secrets[0], title=secrets[1], contact_name=secrets[2], notes="Note ultra secrète"
    )
    run = await intake_runner(tracker(reply), text=text)
    values = field_values(await run.question())
    await run.answer({"choice": "cancel"})
    await run.wait_status("completed")
    second = await intake_runner(tracker(reply), text=text)
    await second.question()
    await second.answer({"choice": "create", "fields": values})
    await second.wait_status("completed")
    for secret in (*secrets, "Note ultra secrète", text):
        assert secret not in caplog.text


async def test_edited_to_apply_drops_the_date(
    intake_runner: MakeIntake, intake_store: FakeApplicationStore
) -> None:
    run = await intake_runner()
    values = field_values(await run.question()) | {"status": "to_apply"}
    await run.answer({"choice": "create", "fields": values})
    await run.wait_status("completed")
    [draft] = intake_store.drafts
    assert (draft.status, draft.applied_on) == ("to_apply", None)
