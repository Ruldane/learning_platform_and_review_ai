"""Tâche « J-7 » (D91) : chaque programme validé de chaque utilisateur, identifiants seulement ;
une panne sur un programme n'arrête pas les autres."""

import logging

import pytest

from app.features.lessons.service import production
from app.features.program.service.runtime import ProgramRuntime
from app.scheduler.base import JobContext
from app.scheduler.jobs import lessons_due
from tests.features.lessons.conftest import (
    ME,
    OTHER,
    RecordingLauncher,
    draft_program,
    validate,
)


async def test_lessons_due_runs_each_validated_program(
    program_rt: ProgramRuntime,
    job_ctx: JobContext,
    launcher: RecordingLauncher,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    launcher.refuse = True  # validés sans leçon lancée : la tâche planifiée rattrape
    mine = await draft_program(program_rt, ME)
    theirs = await draft_program(program_rt, OTHER)
    draft = await draft_program(program_rt, "tiers")  # brouillon : jamais lancé
    await validate(program_rt, mine, ME)
    await validate(program_rt, theirs, OTHER)
    launcher.refuse = False
    await lessons_due.run(job_ctx)
    launched = sorted(entry[1]["program_id"] for entry in launcher.started)
    assert launched == sorted([mine.program_id, theirs.program_id])
    assert draft.program_id not in launched
    await lessons_due.run(job_ctx)  # rien de plus : les chaînes tournent
    assert len(launcher.started) == 2

    real = production.ensure_lessons

    async def flaky(ctx: object, user_id: str, program_id: str, **kw: object) -> str | None:
        if program_id == mine.program_id:
            raise RuntimeError("texte de l'objectif de January")
        return await real(ctx, user_id, program_id, **kw)  # type: ignore[arg-type]

    monkeypatch.setattr(lessons_due, "ensure_lessons", flaky)
    await lessons_due.run(job_ctx)
    assert "RuntimeError" in caplog.text and "January" not in caplog.text
