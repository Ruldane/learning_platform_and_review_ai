"""Amorçage de l'espace `local` du serveur de bout en bout (`--seed-local`) : l'espace d'un poste
qui a tourné en mode local avant de passer en mode Google, de quoi donner quelque chose à reprendre
à la première connexion (parcours n° 5)."""

from datetime import date

from app.config import Settings
from app.db.engine import create_engine, create_session_factory
from app.features.auth.repository import UserRepository
from app.features.capture.service.journal import add_entry

# La ligne du journal de l'espace `local` (le parcours n° 5 la relit, `frontend/e2e/support`).
LOCAL_CAPTURE_TEXT = "Note prise sur cet ordinateur avant la connexion : relire les jointures SQL."
LOCAL_CAPTURE_REF = "e2e-seed-local"


async def seed_local_space(settings: Settings) -> None:
    """Crée l'utilisateur `local` et une ligne de journal. La base doit déjà être migrée."""
    engine = create_engine(settings.database_url)
    try:
        async with create_session_factory(engine)() as session:
            local = await UserRepository(session).add_local()
            await add_entry(
                session,
                local.id,
                kind="capture",
                text=LOCAL_CAPTURE_TEXT,
                occurred_on=date.today(),
                ref_key=LOCAL_CAPTURE_REF,
            )
            await session.commit()
    finally:
        await engine.dispose()
