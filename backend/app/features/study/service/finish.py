"""End of a guided session (SPEC F14, D103), stored in ONE transaction, under the program lock
taken BEFORE it (F4), guarded by `UPDATE … SET status = 'finished' WHERE status = 'open'`:
replayed (`wrap_up` node relaunched after a stop), it re-reads what is stored and writes
nothing more; a session abandoned meanwhile returns an empty end, writing nothing.

What it writes: the time (`worked_minutes` kept by the route, already bounded by the real
duration; 0 if missing), the block's tasks ticked (`read` and `watch` if January did not
finish before the end, `practice` if the exercise is done, F13), the module's skills raised to
`in_progress` at most (never `validated`: only a quiz or a project validates, 4.5) with `study`
evidence, and only if the session leaves a trace (at least one minute or an answer to a
question: an end stored by the route without a timer or an answer raises nothing, D103 no.
18), one card per missed question (`partial`, `wrong`, `revealed`; never `skipped`), the
summary and a `study_session` log line ("study:{id}"). The changed levels are reflected in
memory after the commit, outside the lock, and caught up on replay (like the quiz). Logs: ids
and numbers only."""

import logging
from dataclasses import asdict
from datetime import date, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.study_port import StudyFinished, StudyOutcome
from app.core.errors import AppError
from app.core.skills import evidence
from app.db.models.program import Module
from app.db.models.skills import SkillLevel
from app.db.models.study import StudySession
from app.features.capture.service.journal import JournalLinks, add_entry
from app.features.memory.service.skill_levels import reflect_skill_levels
from app.features.program.service.followup import tick_tasks
from app.features.program.service.programs import load
from app.features.quiz.service.cards import NewCard, add_cards
from app.features.skills.service import SkillsService
from app.features.study.repository import StudyReadRepository, StudyRepository
from app.features.study.service.runtime import StudyRuntime

logger = logging.getLogger(__name__)

READING = ("read", "watch")
PRACTICE = ("practice",)
CARD_VERDICTS = ("partial", "wrong", "revealed")  # "Skip" creates no card (D103)
CEILING: SkillLevel = "in_progress"  # Never above this level (4.5).
EMPTY = StudyFinished(minutes=0, tasks_done=[], flashcards_created=0, skills=[])
# End stored by the route when the Tutor can no longer conclude: no question is known.
NO_OUTCOME = StudyOutcome(outcomes=[], exercise_done=False, ended_early=True, summary="")


def study_not_found() -> AppError:
    return AppError("study_session_not_found", "Study session not found.", 404)


def _plural(count: int, word: str) -> str:
    return f"{count} {word}{'s' if count != 1 else ''}"


def journal_text(module: str, minutes: int, tasks: int, cards: int) -> str:
    return (
        f"Studied {module} for {minutes} min. {_plural(tasks, 'task')} completed, "
        f"{_plural(cards, 'flashcard')} created."
    )


def finished_of(row: StudySession) -> StudyFinished:
    """The end already stored (replay), or an empty end for an abandoned session."""
    if row.status != "finished":
        return EMPTY
    result: dict[str, Any] = (row.outcome or {}).get("result", {})
    skills = [(str(name), level) for name, level in result.get("skills", [])]
    return StudyFinished(
        minutes=row.minutes,
        tasks_done=[str(t) for t in result.get("tasks_done", [])],
        flashcards_created=int(result.get("flashcards_created", 0)),
        skills=skills,
    )


def _ticked_types(outcome: StudyOutcome) -> tuple[str, ...]:
    return (() if outcome.ended_early else READING) + (PRACTICE if outcome.exercise_done else ())


def _cards(row: StudySession, outcome: StudyOutcome) -> list[NewCard]:
    return [
        NewCard(o.question, o.expected, None, row.module_id, "study", row.id)
        for o in outcome.outcomes
        if o.verdict in CARD_VERDICTS and o.expected.strip()
    ]


async def _module(db: AsyncSession, row: StudySession) -> Module | None:
    assert row.program_id is not None  # required target of a guided session
    loaded = await load(db, row.user_id, row.program_id)
    return next((m for m in loaded.modules if m.id == row.module_id), None)


async def _title(db: AsyncSession, row: StudySession, module: Module | None) -> str:
    if module is not None:
        return module.title
    return (await StudyReadRepository(db, row.user_id).titles(row.lesson_id, ""))[0]


def _has_trace(minutes: int, outcome: StudyOutcome) -> bool:
    """At least one minute of work or an answer to a question (D103 no. 18)."""
    return minutes > 0 or bool(outcome.outcomes)


async def _write(
    rt: StudyRuntime, db: AsyncSession, row: StudySession, outcome: StudyOutcome, now: datetime
) -> tuple[StudyFinished, str]:
    """Stores the end (the session has just been claimed `finished`); does not commit."""
    user_id, today = row.user_id, await rt.today(db, row.user_id)
    reads = StudyReadRepository(db, user_id)
    module = await _module(db, row)
    title = await _title(db, row, module)
    minutes = row.worked_minutes or 0
    wanted = _ticked_types(outcome)
    block = [str(t) for t in row.task_ids]
    types = {t.id: t.type for t in await reads.tasks(block)}
    ids = [t for t in block if types.get(t) in wanted]  # in the block's order
    done = await tick_tasks(db, rt.program, user_id, ids)
    skills = [str(s) for s in module.skills] if module and _has_trace(minutes, outcome) else []
    label = f"Guided study of “{title}” ({today.isoformat()})"
    changed = await SkillsService(db, user_id).raise_levels(
        skills, CEILING, evidence("study", row.id, label, now)
    )
    cards = await add_cards(db, user_id, _cards(row, outcome), today)
    result = StudyFinished(minutes, done, cards, changed)
    row.minutes, row.summary = minutes, outcome.summary.strip() or None
    row.outcome = {"outcome": asdict(outcome), "result": asdict(result)}
    await db.flush()
    await _journal(db, row, title, result, today)
    return result, title


async def _journal(
    db: AsyncSession, row: StudySession, title: str, result: StudyFinished, today: date
) -> None:
    await add_entry(
        db,
        row.user_id,
        kind="study_session",
        text=journal_text(title, result.minutes, len(result.tasks_done), result.flashcards_created),
        occurred_on=today,
        ref_key=f"study:{row.id}",
        links=JournalLinks(session_id=row.session_id, study_session_id=row.id),
        data={"lesson_id": row.lesson_id, "minutes": result.minutes, "summary": row.summary},
    )


async def _claim_and_write(
    rt: StudyRuntime, user_id: str, study_id: str, outcome: StudyOutcome
) -> tuple[StudyFinished, bool, str]:
    async with rt.session_factory() as db:
        repo = StudyRepository(db, user_id)
        now = rt.now()
        claimed = await repo.close_open(study_id, status="finished", ended_at=now)
        row = await repo.get_fresh(study_id)
        if row is None or row.kind != "guided" or row.program_id is None:
            raise study_not_found()
        if not claimed:
            done = finished_of(row)
            # The title only serves the caught-up reflection (nothing to reflect: no extra read).
            return done, False, await _title(db, row, await _module(db, row)) if done.skills else ""
        result, title = await _write(rt, db, row, outcome, now)
        await db.commit()
    return result, True, title


async def finish_study(
    rt: StudyRuntime, user_id: str, session_id: str | None, study_id: str, outcome: StudyOutcome
) -> StudyFinished:
    """The end stored once only (see the module); 404 for another user's session.
    `session_id`: the agent session that stores it (`None`: the route, session already dead)."""
    async with rt.session_factory() as db:
        row = await StudyRepository(db, user_id).get_fresh(study_id)
        if row is None or row.kind != "guided" or row.program_id is None:
            raise study_not_found()
        program_id = row.program_id
    # F4: the program lock BEFORE the write transaction (same order as `editing`).
    async with rt.program.program_lock(user_id, program_id):
        result, written, title = await _claim_and_write(rt, user_id, study_id, outcome)
    if result.skills:  # on replay too: idempotent reflection, never lowered (catches up a stop)
        try:
            await reflect_skill_levels(
                rt.memory,
                user_id,
                result.skills,
                author="tutor",
                session_id=session_id,
                reason=f"Guided study of “{title}”",
            )
        except Exception:
            logger.warning("Learned items not reflected after a guided session: study %s", study_id)
    if written:
        logger.info(
            "Guided session stored: study %s, %d min, %d task(s), %d card(s), %d learned item(s)",
            study_id,
            result.minutes,
            len(result.tasks_done),
            result.flashcards_created,
            len(result.skills),
        )
    return result
