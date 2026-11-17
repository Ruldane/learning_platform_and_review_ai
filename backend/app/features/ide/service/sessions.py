"""Séances de code : les fichiers en cours (au plus 20, 200 Ko), le fichier d'entrée, la première
vérification réussie (`passed_at`)."""

import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.db.models.ide import IdeSession
from app.features.ide.hashing import file_hash, is_file_hash
from app.features.ide.repository import ExerciseRepository, PreferenceRepository, SessionRepository
from app.features.ide.service.context import IdeContext
from app.features.ide.service.errors import (
    base_hash_required,
    entry_invalid,
    entry_missing,
    exercise_not_found,
    files_too_large,
    mcp_ide_write_off,
    mcp_write_one_file,
    session_not_found,
    stale_base,
)
from app.providers.sandbox.base import MAX_FILES, MAX_TOTAL_BYTES, check_file_name

logger = logging.getLogger(__name__)

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


async def write_file_as_claude(
    ctx: IdeContext, session_id: str, files: dict[str, str], base_hash: str | None
) -> IdeSession:
    """Claude (MCP) écrit **un** fichier, les autres sont gardés. Seulement si January a allumé
    l'interrupteur (403 `mcp_ide_write_off`, jamais de contenu dans le message ni le journal) ;
    `base_hash` doit être le sha256 du contenu actuel (texte vide pour un nouveau fichier), sinon
    409 `stale_base` : on n'écrase jamais ce que January vient de taper. L'entrée ne change pas."""
    session = await get(ctx, session_id)
    prefs = await PreferenceRepository(ctx.db, ctx.user_id).mine()
    if prefs is None or not prefs.mcp_can_write_files:
        logger.info("mcp_ide_write_off : écriture refusée dans la séance %s", session.id)
        raise mcp_ide_write_off()
    if len(files) != 1:
        raise mcp_write_one_file()
    ((name, text),) = files.items()
    if not is_file_hash(base_hash):
        raise base_hash_required()
    current = session.files.get(name)
    if base_hash != file_hash("" if current is None else str(current)):
        logger.info("stale_base : écriture refusée dans la séance %s", session.id)
        raise stale_base()
    merged = {**session.files, name: text}
    check_files(merged, session.entry)
    session.files = merged
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
