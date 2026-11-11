from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    """Session de la requête : commit en fin de requête, rollback sur erreur."""
    async with request.app.state.session_factory() as session:
        try:
            yield session
            await session.commit()
        except BaseException:
            await session.rollback()
            raise


# `scope="function"` : le code après `yield` (le commit) s'exécute AVANT l'envoi de la réponse.
# Avec la portée « request » par défaut, un échec de commit serait signalé après un 200 déjà
# parti, et le client pourrait lire avant que la donnée ne soit commitée. À utiliser partout.
Db = Annotated[AsyncSession, Depends(get_db, scope="function")]
