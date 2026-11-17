"""Exercices de l'IDE : écrits à la main, générés par le graphe ou ajoutés par Claude. Un fichier
d'exercice n'est jamais exécuté ici : seul le bac à sable (`runs`) exécute du code."""

from app.core.caller import Caller
from app.db.models.ide import ExerciseOrigin, IdeExercise
from app.features.ide.repository import ExerciseRepository
from app.features.ide.schemas import ExerciseIn
from app.features.ide.service.context import IdeContext
from app.features.ide.service.errors import entry_invalid, exercise_not_found
from app.providers.sandbox.base import check_file_name


def origin_of(caller: Caller) -> ExerciseOrigin:
    """Claude (par le MCP) ou January (l'interface) ; le graphe des exercices le dit lui-même."""
    return "claude" if caller.kind == "mcp" else "user"


async def create(
    ctx: IdeContext,
    data: ExerciseIn,
    *,
    origin: ExerciseOrigin | None = None,
    topic: str | None = None,
    agent_session_id: str | None = None,
) -> IdeExercise:
    try:
        check_file_name(data.entry)
    except ValueError:
        raise entry_invalid() from None
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
