"""Le port de l'IDE vu par les agents (10.A3, `IdeStore`) : ce que le professeur lit et écrit, et la
vérification des exercices générés dans le bac à sable. Chaque appel ouvre sa propre session de base
de données (les nœuds tournent hors requête) ; le professeur écrit par `IdeService` sous l'appelant
interne « professor » : mêmes validations et même table de notes que Claude (P8). Rien de ce que
le code d'une utilisatrice contient n'est journalisé."""

import asyncio
import logging
from time import monotonic
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.tools.ide_port import NoteView, RunView, TeachInputs, Verification
from app.agents.tools.ide_schema import ExerciseDraft, TeacherNote
from app.core.errors import AppError
from app.core.providers import Providers
from app.db.models.ide import IdeNote
from app.features.ide.repository import (
    ExerciseRepository,
    NoteRepository,
    PreferenceRepository,
    RunRepository,
)
from app.features.ide.schemas import ExerciseIn, NoteIn
from app.features.ide.service import IdeService, sessions
from app.features.ide.service.context import IdeContext
from app.features.ide.service.teaching import PROFESSOR
from app.providers.sandbox.base import CodeSandbox, SandboxJob, UnknownRun

logger = logging.getLogger(__name__)

NOTES_SEEN = 30  # les notes relues (les 12 derniers messages en sont tirés, renvois exclus)
VERIFY_TIMEOUT_S = 15  # durée réelle demandée au bac pour les tests d'un exercice
VERIFY_WAIT_S = 40.0  # attente totale du résultat (file d'attente comprise)
POLL_S = 0.3
STALE_CODES = frozenset({"note_stale", "note_invalid"})


def _view(note: IdeNote) -> NoteView:
    return NoteView(
        id=note.id,
        kind=note.kind,
        author=note.author,
        level=note.level,
        file_path=note.file_path,
        line_start=note.line_start,
        text=note.content,
        error_key=note.error_key,
    )


class AgentIdeStore:
    """`providers` : lu à chaque appel (le bac à sable est posé par la composition, ou par un
    test)."""

    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession], providers: Providers
    ) -> None:
        self._factory = session_factory
        self._providers = providers

    def _ctx(self, db: AsyncSession, user_id: str) -> IdeContext:
        return IdeContext(db, user_id, self._providers.sandbox, PROFESSOR)

    async def teacher_inputs(
        self, user_id: str, ide_session_id: str, run_id: str | None
    ) -> TeachInputs:
        async with self._factory() as db:
            session = await sessions.get(self._ctx(db, user_id), ide_session_id)
            statement = None
            if session.exercise_id is not None:  # supprimé depuis : la séance garde son titre
                exercise = await ExerciseRepository(db, user_id).get(session.exercise_id)
                statement = exercise.statement if exercise is not None else None
            runs = RunRepository(db, user_id)
            run = await runs.get_fresh(run_id) if run_id else None
            if run is None or run.session_id != session.id:
                run = await runs.latest_of_session(session.id)
            prefs = await PreferenceRepository(db, user_id).mine()
            rows = await NoteRepository(db, user_id).of_session(session.id)
            return TeachInputs(
                title=session.title,
                statement=statement,
                files={str(path): str(text) for path, text in session.files.items()},
                entry=session.entry,
                passed=session.passed,
                style="pair" if prefs is not None and prefs.teacher_style == "pair" else "guide",
                run=None
                if run is None
                else RunView(
                    id=run.id,
                    kind=run.kind,
                    status=run.status,
                    exit_code=run.exit_code,
                    output=run.output,
                    error_signature=run.error_signature,
                ),
                notes=[_view(row) for row in rows[-NOTES_SEEN:]],
            )

    async def save_note(
        self,
        user_id: str,
        ide_session_id: str,
        note: TeacherNote,
        *,
        base_hash: str | None,
        error_key: str | None,
    ) -> str | None:
        """Range la note ; `None` si le code a changé depuis la lecture (proposition périmée) ou si
        la note n'est plus valable : rien n'est rangé."""
        async with self._factory() as db:
            service = IdeService(db, user_id, None, PROFESSOR)
            try:
                data = NoteIn(
                    kind=note.kind,
                    content=note.text,
                    file_path=note.path,
                    line_start=note.start_line,
                    line_end=note.end_line,
                    replacement=note.replacement,
                    base_hash=base_hash,
                )
                saved = await service.add_note(
                    ide_session_id, data, error_key=error_key, level=note.level
                )
            except ValidationError:
                logger.info(
                    "Note du professeur refusée : séance %s, champs invalides", ide_session_id
                )
                return None
            except AppError as exc:
                if exc.code not in STALE_CODES:
                    raise
                logger.info("Note du professeur périmée : séance %s, %s", ide_session_id, exc.code)
                await db.rollback()
                return None
            await db.commit()
            return saved.id

    async def verify(self, user_id: str, draft: ExerciseDraft) -> Verification:
        """Les tests de l'exercice sur sa solution, dans le bac à sable (jamais ici). Les fichiers
        de test de l'exercice sont remis par-dessus la solution : elle ne peut pas les changer.
        Des fichiers ou des noms refusés comptent comme un échec lisible."""
        try:
            ExerciseIn(
                title=draft.title,
                statement=draft.statement,
                files=draft.files,
                entry=draft.entry,
            )
        except ValidationError:
            return Verification(False, "refused", "Les fichiers de l'exercice sont refusés.")
        tests = {name: text for name, text in draft.files.items() if _is_test(name)}
        job = SandboxJob(
            run_id=uuid4().hex,
            files={**draft.solution, **tests},
            entry=draft.entry,
            kind="check",
            timeout_s=VERIFY_TIMEOUT_S,
        )
        sandbox = self._providers.sandbox
        if sandbox is None:
            raise AppError("sandbox_unavailable", "The code sandbox is unavailable.", 503)
        try:
            await sandbox.submit(job)
        except ValueError:
            return Verification(False, "refused", "La solution dépasse les limites du bac.")
        except OSError:
            raise AppError("sandbox_unavailable", "The code sandbox is unavailable.", 503) from None
        return await _result(sandbox, job.run_id)

    async def save_exercise(
        self, user_id: str, agent_session_id: str, draft: ExerciseDraft, topic: str
    ) -> str:
        """Range l'exercice vérifié (origine `generated`) ; la solution n'est jamais rangée."""
        async with self._factory() as db:
            data = ExerciseIn(
                title=draft.title,
                statement=draft.statement,
                files=draft.files,
                entry=draft.entry,
            )
            saved = await IdeService(db, user_id, None, PROFESSOR).create_exercise(
                data, origin="generated", topic=topic, agent_session_id=agent_session_id
            )
            await db.commit()
            return saved.id


def _is_test(name: str) -> bool:
    return name.rsplit("/", 1)[-1].startswith("test_")


async def _result(box: CodeSandbox, run_id: str) -> Verification:
    """Interroge le bac jusqu'à la fin du travail (au plus `VERIFY_WAIT_S`)."""
    started = monotonic()
    while True:
        try:
            progress = await box.poll(run_id, 0)
        except UnknownRun:
            return Verification(False, "error", "Le bac n'a pas rendu de résultat.")
        except OSError:
            raise AppError("sandbox_unavailable", "The code sandbox is unavailable.", 503) from None
        if progress.result is not None:
            ok = progress.result.status == "done" and progress.result.exit_code == 0
            return Verification(ok, progress.result.status, progress.output)
        if monotonic() - started > VERIFY_WAIT_S:
            await box.cancel(run_id)
            return Verification(False, "timeout", progress.output)
        await asyncio.sleep(POLL_S)
