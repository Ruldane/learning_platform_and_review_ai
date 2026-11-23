"""Notes de séance (P8, P9) : indices, explications, annotations, propositions, renvois. Le
professeur interne, Claude (par le MCP) et January écrivent par le même service ; seul l'auteur,
tiré de l'appelant, change. Une proposition remplace une plage de lignes d'un fichier et porte
l'empreinte (sha256) du fichier qu'elle a lu : elle ne s'applique que si le fichier n'a pas
changé. `accept` et `reject` sont des gestes de l'interface (exclus du MCP)."""

from app.core.caller import MCP_CONFIRMED, Caller
from app.db.models.ide import IdeNote, IdeSession, NoteAuthor
from app.features.ide.hashing import is_file_hash
from app.features.ide.repository import NoteRepository
from app.features.ide.schemas import QUESTION_MAX, NoteIn
from app.features.ide.service import sessions
from app.features.ide.service.context import IdeContext, file_hash
from app.features.ide.service.errors import (
    files_too_large,
    mcp_gesture_forbidden,
    not_a_proposal,
    note_closed,
    note_invalid,
    note_not_found,
    note_stale,
)
from app.providers.sandbox.base import MAX_TOTAL_BYTES

# Étiquette de l'appelant interne du professeur (graphe `ide_teacher`, 10.A3). Un jeton MCP n'y
# accède jamais : tout appel MCP est `claude`, quelle que soit l'étiquette du jeton.
PROFESSOR_LABEL = "professor"


def author_of(caller: Caller) -> tuple[NoteAuthor, str | None]:
    """`(auteur, étiquette)` : Claude porte l'étiquette de son jeton, le professeur interne et
    January n'en ont pas."""
    if caller.kind == "mcp":
        return "claude", caller.label[:60]
    return ("professor" if caller.label == PROFESSOR_LABEL else "user"), None


def line_count(text: str) -> int:
    """Le nombre de lignes d'un fichier (au moins 1 : un fichier vide se remplit)."""
    return max(1, len(text.split("\n")) - (1 if text.endswith("\n") else 0))


def apply_replacement(text: str, start: int, end: int, replacement: str) -> str:
    """Remplace les lignes `start` à `end` (de 1, bornes comprises) par `replacement` ; un retour
    à la ligne final du remplacement n'ajoute pas de ligne vide ; un remplacement vide les
    supprime."""
    parts = text.split("\n")
    body = replacement[:-1] if replacement.endswith("\n") else replacement
    parts[start - 1 : end] = body.split("\n") if body else []
    return "\n".join(parts)


def _check_place(session: IdeSession, data: NoteIn) -> str | None:
    """Le fichier visé (s'il y en a un) existe, la plage tient dedans. Rend son contenu."""
    if data.file_path is None:
        if data.line_start is not None or data.line_end is not None:
            raise note_invalid("Des lignes demandent un fichier.")
        return None
    text = session.files.get(data.file_path)
    if text is None:
        raise note_invalid("Ce fichier ne fait pas partie de la séance.")
    start, end = data.line_start, data.line_end
    if end is not None and start is None:
        raise note_invalid("La ligne de fin demande une ligne de début.")
    if start is not None:
        last = end if end is not None else start
        if start > last or last > line_count(str(text)):
            raise note_invalid("Les lignes visées ne sont pas dans le fichier.")
    return str(text)


def _check_proposal(data: NoteIn, text: str | None) -> None:
    """Une proposition : fichier, plage, remplacement et empreinte valide du fichier lu."""
    if text is None or data.line_start is None or data.replacement is None:
        raise note_invalid("Une proposition demande un fichier, une plage de lignes et un texte.")
    if not is_file_hash(data.base_hash):
        raise note_invalid(
            "Une proposition demande l'empreinte sha256 du fichier lu (file_hashes de la séance)."
        )
    if data.base_hash != file_hash(text):
        raise note_stale()


async def add(
    ctx: IdeContext,
    session_id: str,
    data: NoteIn,
    *,
    reference_note_id: str | None = None,
    error_key: str | None = None,
    level: int | None = None,
) -> IdeNote:
    """Ajoute une note ; l'auteur vient de l'appelant. `reference_note_id`, `error_key` et `level`
    (niveau d'un indice gradué) sont ceux du professeur interne, jamais du corps d'une requête."""
    session = await sessions.get(ctx, session_id)
    repo = NoteRepository(ctx.db, ctx.user_id)
    if data.kind != "proposal" and (data.replacement is not None or data.base_hash is not None):
        raise note_invalid("Seule une proposition porte un texte de remplacement et une empreinte.")
    author, label = author_of(ctx.caller)
    if data.kind == "question" and (author != "user" or len(data.content) > QUESTION_MAX):
        raise note_invalid("Une question est celle de January, et tient en 2 000 caractères.")
    text = _check_place(session, data)
    if data.kind == "proposal":
        _check_proposal(data, text)
    if reference_note_id is not None and await repo.get(reference_note_id) is None:
        raise note_invalid("La note citée est introuvable.")
    return await repo.add(
        session_id=session.id,
        kind=data.kind,
        author=author,
        author_label=label,
        origin=ctx.caller.kind,
        file_path=data.file_path,
        line_start=data.line_start,
        line_end=data.line_end or (data.line_start if data.kind == "proposal" else None),
        content=data.content,
        replacement=data.replacement,
        base_hash=data.base_hash,
        reference_note_id=reference_note_id,
        error_key=error_key,
        level=level,
    )


async def list_for(ctx: IdeContext, session_id: str) -> list[IdeNote]:
    session = await sessions.get(ctx, session_id)
    return await NoteRepository(ctx.db, ctx.user_id).of_session(session.id)


async def get(ctx: IdeContext, note_id: str) -> IdeNote:
    note = await NoteRepository(ctx.db, ctx.user_id).get_fresh(note_id)
    if note is None:
        raise note_not_found()
    return note


async def sweep_stale(ctx: IdeContext, session: IdeSession) -> None:
    """Les propositions ouvertes dont le fichier a changé depuis leur lecture deviennent `stale`
    (après une sauvegarde des fichiers)."""
    for proposal in await NoteRepository(ctx.db, ctx.user_id).open_proposals(session.id):
        text = session.files.get(proposal.file_path or "")
        if text is None or file_hash(str(text)) != proposal.base_hash:
            proposal.status = "stale"
    await ctx.db.flush()


def _gesture_of_january(ctx: IdeContext) -> None:
    """Une proposition se décide dans l'interface ou après une confirmation MCP."""
    if ctx.caller.kind == "mcp" and not MCP_CONFIRMED.get():
        raise mcp_gesture_forbidden()


async def accept(ctx: IdeContext, note_id: str) -> IdeSession:
    """Applique la proposition si son fichier n'a pas changé ; sinon elle passe à `stale`
    (enregistré tout de suite : l'erreur 409 défait la transaction de la requête)."""
    _gesture_of_january(ctx)
    note = await get(ctx, note_id)
    if note.kind != "proposal":
        raise not_a_proposal()
    if note.status not in ("open", "stale"):
        raise note_closed()
    session = await sessions.get(ctx, note.session_id)
    current = session.files.get(note.file_path or "")
    here = None if current is None else file_hash(str(current))
    if note.status == "stale" or here != note.base_hash:
        if note.status != "stale":
            note.status = "stale"
            await ctx.db.commit()
        raise note_stale()
    assert current is not None and note.line_start is not None  # garanti par `add`
    changed = apply_replacement(
        str(current), note.line_start, note.line_end or note.line_start, note.replacement or ""
    )
    files = {**session.files, str(note.file_path): changed}
    if sum(len(text.encode()) for text in map(str, files.values())) > MAX_TOTAL_BYTES:
        raise files_too_large()
    if not await sessions.claim_files(ctx, session):
        raise note_stale()
    session.files = files
    note.status = "accepted"
    await ctx.db.flush()
    await sweep_stale(ctx, session)
    return session


async def reject(ctx: IdeContext, note_id: str) -> IdeNote:
    """Refuse une proposition ouverte ou périmée (rien n'est écrit dans les fichiers)."""
    _gesture_of_january(ctx)
    note = await get(ctx, note_id)
    if note.kind != "proposal":
        raise not_a_proposal()
    if note.status == "accepted":
        raise note_closed()
    note.status = "rejected"
    await ctx.db.flush()
    return note
