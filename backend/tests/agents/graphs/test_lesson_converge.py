"""Convergence du Rédacteur et du Vérificateur (D97 n° 11), rejouée avec les affirmations du cas
réel anonymisé de la fin de phase 4 : hors des sections de faits, une affirmation n'est pas
jugée ; après la dernière révision, les phrases encore non sourcées sont retirées par le code,
sans appel au modèle, ou la leçon échoue avec la raison (faux LLM, faux port, vraie base)."""

import logging

import pytest

from app.agents.nodes.verifier import MAX_REVISIONS, check_lesson
from tests.agents.graphs.lesson_support import MakeLesson, claims
from tests.support.lessons import MODULE_ID, PROGRAM_ID, TITLE
from tests.support.verifier_case import (
    C_ABSENT,
    C_APPS,
    C_NAME,
    C_OBJECTIVE,
    C_PIP,
    C_PREREQUISITE,
    C_TERMINAL,
    OBJECTIVE,
    real_case_lesson,
)

LESSON = real_case_lesson()


async def test_last_round_removes_unsupported_sentences_and_publishes(
    make_lesson_runner: MakeLesson, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="app")
    rounds = [claims(C_NAME), claims(C_TERMINAL), claims(C_APPS, C_OBJECTIVE)]
    c = await make_lesson_runner(writer=[LESSON] * 3, verifier=rounds)
    await c.wait_status("completed")
    assert MAX_REVISIONS == 2 and c.writer_calls == 3
    assert len(c.prompts_of("verifier")) == 3  # aucun appel de plus pour le retrait
    pub = c.store.published[0]
    assert "construire des applications" not in pub.markdown
    assert OBJECTIVE in pub.markdown  # hors périmètre : rien n'est retiré
    assert "Pour le métier visé par Alice" in pub.markdown
    words = check_lesson(pub.markdown, title=TITLE, sources=[]).words
    assert pub.report.words == words and pub.report.revisions == 2
    texts = [m["text"] for m in await c.events("agent.message")]
    assert any("Leçon conforme après retrait de 1 phrase(s)" in t for t in texts)
    assert "1 phrase(s) retirée(s)" in caplog.text and "1 hors périmètre" in caplog.text
    for content in ("applications", "Alice", "Python", "VS Code"):
        assert content not in caplog.text


async def test_out_of_scope_claims_need_no_revision(make_lesson_runner: MakeLesson) -> None:
    c = await make_lesson_runner(writer=[LESSON], verifier=[claims(C_OBJECTIVE, C_PREREQUISITE)])
    await c.wait_status("completed")
    assert c.writer_calls == 1
    assert c.store.published[0].markdown == LESSON.strip()


async def test_earlier_rounds_ask_the_writer_instead_of_removing(
    make_lesson_runner: MakeLesson,
) -> None:
    c = await make_lesson_runner(writer=[LESSON, LESSON], verifier=[claims(C_APPS)])
    await c.wait_status("completed")
    assert c.writer_calls == 2
    assert f"Affirmation non sourcée : {C_APPS}" in c.prompt_of_writer(2)
    assert "construire des applications" in c.store.published[0].markdown


async def test_unlocated_claim_after_last_revision_fails_the_lesson(
    make_lesson_runner: MakeLesson,
) -> None:
    c = await make_lesson_runner(writer=[LESSON] * 3, verifier=[claims(C_APPS, C_ABSENT)] * 3)
    await c.wait_status("completed")
    assert c.store.published == [] and len(c.store.failures) == 1
    module, reason = c.store.failures[0]
    assert module == MODULE_ID and "1 affirmation(s) non sourcée(s) introuvable(s)" in reason
    assert c.store.next_calls == [(PROGRAM_ID, c.sid)]


async def test_removal_that_breaks_the_checks_fails_the_lesson(
    make_lesson_runner: MakeLesson,
) -> None:
    c = await make_lesson_runner(writer=[LESSON] * 3, verifier=[claims(C_PIP)] * 3)
    await c.wait_status("completed")
    assert c.store.published == []
    _module, reason = c.store.failures[0]
    assert "Retrait de 1 phrase(s) non sourcée(s) impossible" in reason
    assert "L'essentiel en 5 lignes" in reason
