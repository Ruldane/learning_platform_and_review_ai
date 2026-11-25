"""The professor's cost gate (10.A3, requirement of 2026-11-14): what is allowed to wake the
model, and launching the `ide_teacher` flow.

The professor reacts to a failing run, a question, a hint request or, optionally, after 30 s
stopped on a line: never to typing, never to a save (no other route launches it). Before any
call, `TeachGate` looks in this order: the **same error at the same place** (reference to the
previous note, no call), **one call at a time** per session, the "on demand" mode and the timer
without the option, then the token **caps** (session, day). A question and a hint request are
explicit gestures: they are always handled (unless a call is already running), even after a
cap. The level of a hint rises from 1 to 3 with the hints already given for the same error."""

import asyncio
import hashlib
import logging
import weakref
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runtime.launcher import SessionLauncher
from app.core.caller import Caller
from app.db.base import utcnow
from app.db.models.ide import IdeNote, IdeRun, IdeSession
from app.features.ide.repository import (
    TEACHER_GRAPH,
    TEACHER_SUBJECT,
    ProfessorNoteRepository,
    RunRepository,
)
from app.features.ide.schemas import (
    ExerciseGenerateIn,
    IdeSessionStarted,
    NoteIn,
    NoteKind,
    SkipReason,
    TeachIn,
    TeachOut,
    TeachTrigger,
)
from app.features.ide.service import notes, sessions
from app.features.ide.service.context import IdeContext
from app.features.ide.service.errors import run_not_found
from app.features.ide.service.notes import PROFESSOR_LABEL
from app.features.ide.service.usage import UsageService
from app.features.sessions.service import find_active_session

EXERCISE_GRAPH = "ide_exercise"
AUTOMATIC: frozenset[str] = frozenset({"run_error", "idle"})
IDLE_DELAY = timedelta(seconds=30)
MAX_LEVEL = 3
COMPLIMENT_KEY = "compliment"
COMPLIMENT = "Your tests pass. Read through your code one more time before finishing."
REFERENCE = "The same error occurred here. The previous note still applies."

PROFESSOR = Caller(kind="app", label=PROFESSOR_LABEL)
JANUARY = Caller(kind="app", label="app")  # the interface: the notes' author is then `user`
logger = logging.getLogger(__name__)
_LOCKS: weakref.WeakValueDictionary[str, asyncio.Lock] = weakref.WeakValueDictionary()


@dataclass(frozen=True)
class GateDecision:
    """`call`: launch the professor (at level `level` for a hint); `reference`: refer to
    the note `note_id`; `skip`: launch nothing, for `reason`."""

    action: Literal["call", "reference", "skip"]
    reason: SkipReason | None = None
    note_id: str | None = None
    level: int = 1


def error_key(*parts: str | None) -> str:
    """The fingerprint (40 characters) of a place or an error: never the text itself."""
    return hashlib.sha1("|".join(part or "" for part in parts).encode()).hexdigest()  # noqa: S324


def signature_of(trigger: str, run: IdeRun | None, body: TeachIn) -> str:
    """The key of the error or place of a trigger: the signature of the last run (error type and
    last line of January's code); otherwise her state; otherwise the given place; otherwise the
    session."""
    place = f"{body.file_path}:{body.line}" if body.file_path and body.line else None
    if trigger == "idle":
        return error_key("idle", place)
    if run is not None and run.error_signature:
        return run.error_signature
    if trigger == "run_error" and run is not None:
        return error_key("run", run.status, run.entry)
    return error_key("place", place) if place else error_key("session")


class TeachGate:
    def __init__(self, db: AsyncSession, user_id: str) -> None:
        self._db = db
        self._user_id = user_id
        self._usage = UsageService(db, user_id)

    async def _busy(self, session_id: str) -> bool:
        found = await find_active_session(
            self._db,
            self._user_id,
            graph=TEACHER_GRAPH,
            subject_type=TEACHER_SUBJECT,
            subject_id=session_id,
        )
        return found is not None

    async def _capped(self, session_id: str, session_cap: int, day_cap: int) -> bool:
        if await self._usage.session_tokens(session_id) >= session_cap:
            return True
        return await self._usage.day_tokens() >= day_cap

    async def decide(self, session_id: str, trigger: str, signature: str | None) -> GateDecision:
        """Call, refer to the previous note, or do nothing (and why)."""
        prefs = await self._usage.preferences()
        given = await ProfessorNoteRepository(self._db, self._user_id).of_professor(session_id)
        same = [note for note in given if signature and note.error_key == signature]
        automatic = trigger in AUTOMATIC
        previous = [note for note in same if note.kind != "reference"]
        if automatic and previous:
            return GateDecision("reference", note_id=previous[-1].id)
        if await self._busy(session_id):
            return GateDecision("skip", reason="busy")
        if automatic:
            if prefs.teacher_mode == "on_demand" or (trigger == "idle" and not prefs.idle_trigger):
                return GateDecision("skip", reason="on_demand")
            if trigger == "idle" and given and utcnow() - given[-1].created_at < IDLE_DELAY:
                return GateDecision("skip", reason="busy")
            if await self._capped(session_id, prefs.session_cap, prefs.day_cap):
                return GateDecision("skip", reason="cap_reached")
        hints = sum(1 for note in same if note.kind == "hint")
        return GateDecision("call", level=min(hints + 1, MAX_LEVEL))


def _lock_of(user_id: str, key: str) -> asyncio.Lock:
    name = f"{user_id}:{key}"
    lock = _LOCKS.get(name)
    if lock is None:
        lock = _LOCKS[name] = asyncio.Lock()
    return lock


class TeachingService:
    """On behalf of a user; the commit belongs to the request."""

    def __init__(self, db: AsyncSession, user_id: str, launcher: SessionLauncher) -> None:
        self._db = db
        self._user_id = user_id
        self._launcher = launcher
        self._ctx = IdeContext(db, user_id, None, PROFESSOR)
        self._january = IdeContext(db, user_id, None, JANUARY)

    async def _run_of(self, session: IdeSession, run_id: str | None) -> IdeRun | None:
        repo = RunRepository(self._db, self._user_id)
        if run_id is None:
            return await repo.latest_of_session(session.id)
        run = await repo.get_fresh(run_id)
        if run is None or run.session_id != session.id:
            raise run_not_found()
        return run

    async def _note(
        self, session: IdeSession, kind: NoteKind, content: str, **fields: Any
    ) -> IdeNote:
        """A professor note without a model call (compliment, reference)."""
        return await notes.add(self._ctx, session.id, NoteIn(kind=kind, content=content), **fields)

    async def _compliment(self, session: IdeSession) -> TeachOut:
        """A successful run: nothing until the session is passed; then, at most one compliment,
        without a model call."""
        if not session.passed:
            return TeachOut(skipped="on_demand")
        given = await ProfessorNoteRepository(self._db, self._user_id).of_professor(session.id)
        found = [note for note in given if note.error_key == COMPLIMENT_KEY]
        if found:
            return TeachOut(reference_note_id=found[0].id)
        note = await self._note(session, "explanation", COMPLIMENT, error_key=COMPLIMENT_KEY)
        return TeachOut(reference_note_id=note.id)

    async def _refer(self, session: IdeSession, previous_id: str, signature: str) -> TeachOut:
        """Same error at the same place: a single reference written per cited note, no call."""
        given = await ProfessorNoteRepository(self._db, self._user_id).of_professor(session.id)
        if not any(note.reference_note_id == previous_id for note in given):
            await self._note(
                session, "reference", REFERENCE, reference_note_id=previous_id, error_key=signature
            )
        return TeachOut(reference_note_id=previous_id)

    async def teach(self, session_id: str, body: TeachIn) -> TeachOut:
        """Only one of the three: the professor's session, a reference, or why nothing launches."""
        session = await sessions.get(self._ctx, session_id)
        trigger: TeachTrigger = body.trigger
        if trigger == "run_ok":
            return await self._compliment(session)
        run = await self._run_of(session, body.run_id)
        signature = signature_of(trigger, run, body)
        async with _lock_of(self._user_id, session.id):
            decision = await TeachGate(self._db, self._user_id).decide(
                session.id, trigger, signature
            )
            if decision.action == "reference":
                return await self._refer(session, str(decision.note_id), signature)
            if decision.action == "skip":
                return TeachOut(skipped=decision.reason)
            path = body.file_path if body.file_path in session.files else None
            question = body.question.strip() if body.question else None
            if trigger == "question" and question:
                # Her question stays in the thread: the professor re-reads it with the next ones.
                await notes.add(
                    self._january, session.id, NoteIn(kind="question", content=question)
                )
                # Stored before the launch: the flow re-reads it, and it writes to the database too.
                await self._db.commit()
                logger.info("Question stored: session %s", session.id)  # never its text
            started = await self._launcher.start(
                self._user_id,
                TEACHER_GRAPH,
                {
                    "ide_session_id": session.id,
                    "trigger": trigger,
                    "question": question,
                    "file_path": path,
                    "line": body.line if path else None,
                    "run_id": run.id if run else None,
                    "error_key": signature,
                    "level": decision.level,
                },
                subject_type=TEACHER_SUBJECT,
                subject_id=session.id,
            )
        return TeachOut(session_id=started)

    async def generate(self, body: ExerciseGenerateIn) -> IdeSessionStarted:
        """Launches the exercises flow: returns right away the agent session to follow."""
        started = await self._launcher.start(
            self._user_id,
            EXERCISE_GRAPH,
            {"topic": body.topic, "level": body.level},
            subject_type="ide_exercise",
        )
        return IdeSessionStarted(session_id=started)
