"""Exercices de l'IDE : écrits à la main, générés par le graphe ou ajoutés par Claude. Un fichier
d'exercice n'est jamais exécuté ici : seul le bac à sable (`runs`) exécute du code."""

from app.core.caller import Caller
from app.db.models.ide import ExerciseOrigin, IdeExercise
from app.features.ide.repository import ExerciseRepository
from app.features.ide.schemas import ExerciseIn, ExercisePatch
from app.features.ide.service.context import IdeContext
from app.features.ide.service.errors import entry_invalid, exercise_not_found
from app.providers.sandbox.base import check_file_name


def origin_of(caller: Caller) -> ExerciseOrigin:
    """Claude (par le MCP) ou January (l'interface) ; le graphe des exercices le dit lui-même."""
    return "claude" if caller.kind == "mcp" else "user"


def _check_entry(files: dict[str, str], entry: str) -> None:
    """Le fichier d'entrée est un chemin permis et, quand l'exercice a des fichiers, l'un d'eux
    (sinon la séance ne s'exécuterait pas : `check_job_limits`)."""
    try:
        check_file_name(entry)
    except ValueError:
        raise entry_invalid() from None
    if files and entry not in files:
        raise entry_invalid()


async def create(
    ctx: IdeContext,
    data: ExerciseIn,
    *,
    origin: ExerciseOrigin | None = None,
    topic: str | None = None,
    agent_session_id: str | None = None,
) -> IdeExercise:
    _check_entry(dict(data.files), data.entry)
    return await ExerciseRepository(ctx.db, ctx.user_id).add(
        title=data.title,
        statement=data.statement,
        files=dict(data.files),
        entry=data.entry,
        origin=origin or origin_of(ctx.caller),
        topic=topic,
        session_id=agent_session_id,
    )


async def get(ctx: IdeContext, exercise_id: str) -> IdeExercise:
    found = await ExerciseRepository(ctx.db, ctx.user_id).get(exercise_id)
    if found is None:
        raise exercise_not_found()
    return found


async def list_all(ctx: IdeContext) -> list[IdeExercise]:
    return await ExerciseRepository(ctx.db, ctx.user_id).newest_first()


async def delete(ctx: IdeContext, exercise_id: str) -> None:
    """Supprime l'exercice ; ses séances restent (aucune clé étrangère)."""
    if not await ExerciseRepository(ctx.db, ctx.user_id).delete(exercise_id):
        raise exercise_not_found()


async def update(ctx: IdeContext, exercise_id: str, patch: ExercisePatch) -> IdeExercise:
    """Retouche l'exercice (titre, énoncé, fichiers, fichier d'entrée) ; le sujet ne change pas,
    les séances déjà ouvertes gardent leurs fichiers. L'origine devient celle de l'appelant quand
    c'est Claude (le texte n'est plus celui d'avant, ni vérifié dans le bac si l'exercice était
    généré). Écriture directe : aucun agent, aucune exécution."""
    row = await get(ctx, exercise_id)
    changes = patch.model_dump(exclude_none=True)
    files = dict(changes.get("files", row.files))
    _check_entry(files, changes.get("entry", row.entry))
    for name, value in changes.items():
        setattr(row, name, dict(value) if name == "files" else value)
    if ctx.caller.kind == "mcp":
        row.origin = "claude"
    await ctx.db.flush()
    return row
