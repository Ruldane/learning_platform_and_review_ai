"""Séances de code : les fichiers en cours (au plus 20, 200 Ko), le fichier d'entrée, la première
vérification réussie (`passed_at`)."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.db.models.ide import IdeSession
from app.features.ide.repository import ExerciseRepository, SessionRepository
from app.features.ide.service.context import IdeContext
from app.features.ide.service.errors import (
    entry_invalid,
    entry_missing,
    exercise_not_found,
    files_too_large,
    session_not_found,
)
from app.providers.sandbox.base import MAX_FILES, MAX_TOTAL_BYTES, check_file_name

DEFAULT_ENTRY = "main.py"
FREE_TITLE = "Séance libre"


@dataclass(frozen=True)
class PassedSession:
    id: str
    title: str
    at: datetime


async def get(ctx: IdeContext, session_id: str) -> IdeSession:
    found = await SessionRepository(ctx.db, ctx.user_id).get_fresh(session_id)
    if found is None:
        raise session_not_found()
    return found


async def list_all(ctx: IdeContext) -> list[IdeSession]:
    return await SessionRepository(ctx.db, ctx.user_id).newest_first()


async def open_session(ctx: IdeContext, exercise_id: str | None, title: str | None) -> IdeSession:
    """Une séance sur les fichiers de départ de l'exercice, ou une séance libre (un `main.py`
    vide). L'exercice d'une autre utilisatrice est introuvable."""
    files: dict[str, str] = {DEFAULT_ENTRY: ""}
    entry = DEFAULT_ENTRY
    name = title or FREE_TITLE
    if exercise_id is not None:
        exercise = await ExerciseRepository(ctx.db, ctx.user_id).get(exercise_id)
        if exercise is None:
            raise exercise_not_found()
        entry = exercise.entry
        files = {str(path): str(text) for path, text in exercise.files.items()}
        files.setdefault(entry, "")
        name = title or exercise.title
    return await SessionRepository(ctx.db, ctx.user_id).add(
        exercise_id=exercise_id, title=name, files=files, entry=entry
    )


def check_files(files: dict[str, str], entry: str) -> None:
    """Les plafonds du bac (20 fichiers, 200 000 octets, noms permis) et l'entrée présente."""
    try:
        check_file_name(entry)
    except ValueError:
        raise entry_invalid() from None
    if not files or entry not in files:
        raise entry_missing()
    size = sum(len(text.encode()) for text in files.values())
    if len(files) > MAX_FILES or size > MAX_TOTAL_BYTES:
        raise files_too_large()


async def save_files(
    ctx: IdeContext, session_id: str, files: dict[str, str], entry: str | None
) -> IdeSession:
    """Remplace les fichiers (geste de l'interface). L'entrée reste celle de la séance sauf si
    `entry` en donne une autre."""
    session = await get(ctx, session_id)
    wanted = entry or session.entry
    check_files(files, wanted)
    session.files = dict(files)
    session.entry = wanted
    session.updated_at = utcnow()
    await ctx.db.flush()
    return session


async def recent_passes(
    db: AsyncSession, user_id: str, after: datetime | None, before: datetime | None, limit: int
) -> list[PassedSession]:
    """Les séances réussies (première vérification) dans `[after, before]`, la plus récente
    d'abord (fil d'activité). Ni fichier ni sortie."""
    rows = await SessionRepository(db, user_id).passed_between(after, before, limit)
    return [PassedSession(row.id, row.title, row.passed_at) for row in rows if row.passed_at]
