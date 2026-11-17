"""Service de l'IDE Python (phase 10) : exercices, séances, exécutions dans le bac à sable, notes.
Au nom d'une utilisatrice ; `caller` dit qui fait le geste (l'interface, le professeur interne ou
Claude par le MCP) : il fixe l'auteur des notes et l'origine des exercices."""

from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.caller import Caller
from app.db.models.ide import ExerciseOrigin
from app.features.ide.schemas import (
    ExerciseIn,
    ExerciseOut,
    IdeSessionOut,
    NoteIn,
    NoteOut,
    RunOut,
    RunProgress,
    SessionSummary,
)
from app.features.ide.service import exercises, notes, runs, sessions
from app.features.ide.service.context import IdeContext, file_hash
from app.features.ide.service.signature import error_signature
from app.providers.sandbox.base import CodeSandbox

__all__ = ["IdeService", "error_signature", "file_hash"]


class IdeService:
    """Le commit appartient à l'appelant (la session de la requête)."""

    def __init__(
        self, db: AsyncSession, user_id: str, sandbox: CodeSandbox | None, caller: Caller
    ) -> None:
        self._ctx = IdeContext(db, user_id, sandbox, caller)

    async def list_exercises(self) -> list[ExerciseOut]:
        return [ExerciseOut.model_validate(row) for row in await exercises.list_all(self._ctx)]

    async def create_exercise(
        self,
        data: ExerciseIn,
        *,
        origin: ExerciseOrigin | None = None,
        topic: str | None = None,
        agent_session_id: str | None = None,
    ) -> ExerciseOut:
        """`origin` suit l'appelant (`user` ou `claude`) ; le graphe des exercices (10.A3) donne
        `generated`, le sujet et sa session d'agents."""
        row = await exercises.create(
            self._ctx, data, origin=origin, topic=topic, agent_session_id=agent_session_id
        )
        return ExerciseOut.model_validate(row)

    async def delete_exercise(self, exercise_id: str) -> None:
        await exercises.delete(self._ctx, exercise_id)

    async def list_sessions(self) -> list[SessionSummary]:
        return [SessionSummary.model_validate(row) for row in await sessions.list_all(self._ctx)]

    async def open_session(
        self, exercise_id: str | None = None, title: str | None = None
    ) -> IdeSessionOut:
        """Une séance sur un exercice, ou une séance libre (sans `exercise_id`)."""
        row = await sessions.open_session(self._ctx, exercise_id, title)
        return IdeSessionOut.model_validate(row)

    async def get_session(self, session_id: str) -> IdeSessionOut:
        return IdeSessionOut.model_validate(await sessions.get(self._ctx, session_id))

    async def save_files(
        self,
        session_id: str,
        files: dict[str, str],
        entry: str | None = None,
        base_hash: str | None = None,
        base_hashes: dict[str, str] | None = None,
    ) -> IdeSessionOut:
        """L'interface remplace les fichiers (20 au plus, 200 Ko). Claude (MCP) écrit un fichier,
        sous l'interrupteur de January et avec `base_hash` (`sessions.write_file_as_claude`). Les
        propositions dont le fichier a changé deviennent `stale`."""
        if self._ctx.caller.kind == "mcp":
            row = await sessions.write_file_as_claude(self._ctx, session_id, files, base_hash)
        else:
            row = await sessions.save_files(self._ctx, session_id, files, entry, base_hashes)
        await notes.sweep_stale(self._ctx, row)
        return IdeSessionOut.model_validate(row)

    async def start_run(
        self, session_id: str, kind: Literal["run", "check"], entry: str | None = None
    ) -> RunOut:
        """Une exécution à la fois par utilisatrice (409 `run_in_progress`) ; bac arrêté : 503
        `sandbox_unavailable`."""
        return RunOut.model_validate(await runs.start(self._ctx, session_id, kind, entry))

    async def list_runs(self, session_id: str) -> list[RunOut]:
        """Les 20 dernières exécutions de la séance, la plus récente d'abord."""
        found = await runs.list_for(self._ctx, session_id)
        return [RunOut.model_validate(row) for row in found]

    async def get_run(self, run_id: str, after: int = 0) -> RunProgress:
        """La sortie depuis l'octet `after` ; fige la sortie et la signature à la fin."""
        return await runs.progress(self._ctx, run_id, after)

    async def list_notes(self, session_id: str) -> list[NoteOut]:
        return [NoteOut.model_validate(row) for row in await notes.list_for(self._ctx, session_id)]

    async def add_note(
        self,
        session_id: str,
        data: NoteIn,
        *,
        reference_note_id: str | None = None,
        error_key: str | None = None,
        level: int | None = None,
    ) -> NoteOut:
        """L'auteur est tiré de l'appelant (`Caller`), jamais du corps."""
        row = await notes.add(
            self._ctx,
            session_id,
            data,
            reference_note_id=reference_note_id,
            error_key=error_key,
            level=level,
        )
        return NoteOut.model_validate(row)

    async def accept_note(self, note_id: str) -> IdeSessionOut:
        """Geste de l'interface : applique la proposition si son fichier n'a pas changé."""
        return IdeSessionOut.model_validate(await notes.accept(self._ctx, note_id))

    async def reject_note(self, note_id: str) -> NoteOut:
        return NoteOut.model_validate(await notes.reject(self._ctx, note_id))
