"""La barrière de coût du professeur (10.A3, exigence du 2026-11-14) : ce qui a le droit de
réveiller le modèle, et le lancement du parcours `ide_teacher`.

Le professeur réagit à une exécution en erreur, à une question, à une demande d'indice ou, en
option, après 30 s d'arrêt sur une ligne : jamais à la frappe, jamais à une sauvegarde (aucune autre
route ne le lance). Avant tout appel, `TeachGate` regarde dans cet ordre : la **même erreur au même
endroit** (renvoi à la note précédente, aucun appel), **un appel à la fois** par séance, le mode
« sur demande » et la minuterie sans option, puis les **plafonds** de jetons (séance, jour). Une
question et une demande d'indice sont des gestes explicites : elles sont toujours traitées (sauf si
un appel court déjà), même après un plafond. Le niveau d'un indice monte de 1 à 3 avec les indices
déjà donnés pour la même erreur."""

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
COMPLIMENT = "Bravo : tes tests passent. Relis ton code une dernière fois, tu peux en être fière."
REFERENCE = "Même erreur au même endroit : relis ma note précédente, elle s'applique encore."

PROFESSOR = Caller(kind="app", label=PROFESSOR_LABEL)
JANUARY = Caller(kind="app", label="app")  # l'interface : l'auteur des notes est alors `user`
logger = logging.getLogger(__name__)
_LOCKS: weakref.WeakValueDictionary[str, asyncio.Lock] = weakref.WeakValueDictionary()


@dataclass(frozen=True)
class GateDecision:
    """`call` : lancer le professeur (au niveau `level` pour un indice) ; `reference` : renvoyer à
    la note `note_id` ; `skip` : ne rien lancer, pour `reason`."""

    action: Literal["call", "reference", "skip"]
    reason: SkipReason | None = None
    note_id: str | None = None
    level: int = 1


def error_key(*parts: str | None) -> str:
    """L'empreinte (40 signes) d'un endroit ou d'une erreur : jamais le texte lui-même."""
    return hashlib.sha1("|".join(part or "" for part in parts).encode()).hexdigest()  # noqa: S324


def signature_of(trigger: str, run: IdeRun | None, body: TeachIn) -> str:
    """La clé de l'erreur ou de l'endroit d'un déclenchement : la signature de la dernière
    exécution (type d'erreur et dernière ligne du code de January) ; sinon son état ; sinon
    l'endroit donné ; sinon la séance."""
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
        """Appeler, renvoyer à la note précédente, ou ne rien faire (et pourquoi)."""
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
    """Au nom d'une utilisatrice ; le commit appartient à la requête."""

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
        """Une note du professeur sans appel de modèle (compliment, renvoi)."""
        return await notes.add(self._ctx, session.id, NoteIn(kind=kind, content=content), **fields)

    async def _compliment(self, session: IdeSession) -> TeachOut:
        """Une exécution réussie : rien tant que la séance n'est pas réussie ; ensuite, au plus un
        compliment, sans appel de modèle."""
        if not session.passed:
            return TeachOut(skipped="on_demand")
        given = await ProfessorNoteRepository(self._db, self._user_id).of_professor(session.id)
        found = [note for note in given if note.error_key == COMPLIMENT_KEY]
        if found:
            return TeachOut(reference_note_id=found[0].id)
        note = await self._note(session, "explanation", COMPLIMENT, error_key=COMPLIMENT_KEY)
        return TeachOut(reference_note_id=note.id)

    async def _refer(self, session: IdeSession, previous_id: str, signature: str) -> TeachOut:
        """Même erreur au même endroit : un seul renvoi écrit par note citée, aucun appel."""
        given = await ProfessorNoteRepository(self._db, self._user_id).of_professor(session.id)
        if not any(note.reference_note_id == previous_id for note in given):
            await self._note(
                session, "reference", REFERENCE, reference_note_id=previous_id, error_key=signature
            )
        return TeachOut(reference_note_id=previous_id)

    async def teach(self, session_id: str, body: TeachIn) -> TeachOut:
        """Un seul des trois : la session du professeur, un renvoi, ou pourquoi rien ne se lance."""
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
                # Sa question reste dans le fil : le professeur la relira avec les suivantes.
                await notes.add(
                    self._january, session.id, NoteIn(kind="question", content=question)
                )
                # Rangée avant le lancement : le parcours la relit, et il écrit lui aussi en base.
                await self._db.commit()
                logger.info("Question rangée : séance %s", session.id)  # jamais son texte
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
        """Lance le parcours des exercices : rend aussitôt la session d'agents à suivre."""
        started = await self._launcher.start(
            self._user_id,
            EXERCISE_GRAPH,
            {"topic": body.topic, "level": body.level},
            subject_type="ide_exercise",
        )
        return IdeSessionStarted(session_id=started)
