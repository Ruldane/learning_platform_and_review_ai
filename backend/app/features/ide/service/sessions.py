"""Séances de code : les fichiers en cours (au plus 20, 200 Ko), le fichier d'entrée, la première
vérification réussie (`passed_at`)."""

import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import set_committed_value

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
    files_changed,
    files_too_large,
    mcp_ide_test_file,
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


async def claim_files(ctx: IdeContext, session: IdeSession) -> bool:
    """Réserve l'écriture des fichiers de la séance lue : la base ne l'accorde que si personne n'a
    écrit depuis la lecture (`files_version` inchangée). Atomique : deux écritures qui partent de la
    même lecture, une seule passe. Faux : relis la séance."""
    read = session.files_version
    taken = await ctx.db.execute(
        update(IdeSession)
        .where(
            IdeSession.id == session.id,
            IdeSession.user_id == ctx.user_id,
            IdeSession.files_version == read,
        )
        .values(files_version=read + 1)
        .execution_options(synchronize_session=False)
    )
    if taken.rowcount == 0:  # type: ignore[attr-defined]
        return False
    set_committed_value(session, "files_version", read + 1)
    return True


def _clashes(session: IdeSession, files: dict[str, str], base_hashes: dict[str, str]) -> list[str]:
    """Les fichiers dont la version du serveur n'est plus celle de `base_hashes` et que `files`
    changerait (envoyer le texte actuel n'efface rien)."""
    clash: list[str] = []
    for name, base in sorted(base_hashes.items()):
        current = str(session.files.get(name, ""))
        if file_hash(current) != base and files.get(name, "") != current:
            clash.append(name)
    # Un fichier que Claude a créé depuis : absent de l'instantané, l'envoi l'effacerait.
    known = base_hashes.keys() | files.keys()
    return sorted({*clash, *(name for name in session.files if name not in known)})


async def save_files(
    ctx: IdeContext,
    session_id: str,
    files: dict[str, str],
    entry: str | None,
    base_hashes: dict[str, str] | None = None,
) -> IdeSession:
    """Remplace les fichiers (geste de l'interface). L'entrée reste celle de la séance sauf si
    `entry` en donne une autre. `base_hashes` (facultatif) : la version sur laquelle chaque fichier
    a été édité ; un fichier que Claude a changé depuis et que l'envoi écraserait donne 409
    `stale_base` (noms seulement), rien n'est écrit."""
    session = await get(ctx, session_id)
    if base_hashes:
        clash = _clashes(session, files, base_hashes)
        if clash:
            logger.info("stale_base : enregistrement refusé dans la séance %s", session.id)
            raise files_changed(clash)
    wanted = entry or session.entry
    check_files(files, wanted)
    if not await claim_files(ctx, session):  # quelqu'un a écrit entre la lecture et ici
        await ctx.db.refresh(session)
        raise files_changed(sorted(files))
    session.files = dict(files)
    session.entry = wanted
    session.updated_at = utcnow()
    await ctx.db.flush()
    return session


def is_test_file(name: str) -> bool:
    """Un fichier que pytest collecte (`test_*.py`, `*_test.py`) ou qui le configure
    (`conftest.py`), où qu'il soit dans les dossiers de la séance."""
    base = name.rsplit("/", 1)[-1]
    return base == "conftest.py" or (
        base.endswith(".py") and (base.startswith("test_") or base.endswith("_test.py"))
    )


async def write_file_as_claude(
    ctx: IdeContext, session_id: str, files: dict[str, str], base_hash: str | None
) -> IdeSession:
    """Claude (MCP) écrit **un** fichier, les autres sont gardés. Seulement si January a allumé
    l'interrupteur (403 `mcp_ide_write_off`, jamais de contenu dans le message ni le journal) ;
    `base_hash` doit être le sha256 du contenu actuel (texte vide pour un nouveau fichier), sinon
    409 `stale_base` : on n'écrase jamais ce que January vient de taper. L'entrée ne change pas.
    Dans une séance sur exercice, jamais un fichier de test (403 `mcp_ide_test_file`) : ce sont les
    siens."""
    session = await get(ctx, session_id)
    prefs = await PreferenceRepository(ctx.db, ctx.user_id).mine()
    if prefs is None or not prefs.mcp_can_write_files:
        logger.info("mcp_ide_write_off : écriture refusée dans la séance %s", session.id)
        raise mcp_ide_write_off()
    if len(files) != 1:
        raise mcp_write_one_file()
    ((name, text),) = files.items()
    if session.exercise_id is not None and is_test_file(name):
        logger.info("mcp_ide_test_file : écriture refusée dans la séance %s", session.id)
        raise mcp_ide_test_file()
    if not is_file_hash(base_hash):
        raise base_hash_required()
    current = session.files.get(name)
    if base_hash != file_hash("" if current is None else str(current)):
        logger.info("stale_base : écriture refusée dans la séance %s", session.id)
        raise stale_base()
    merged = {**session.files, name: text}
    check_files(merged, session.entry)
    if not await claim_files(ctx, session):
        logger.info("stale_base : écriture concurrente refusée dans la séance %s", session.id)
        raise stale_base()
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
