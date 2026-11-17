"""Ce que les opérations du service de l'IDE partagent : la session de base de données, la
propriétaire, le bac à sable (`None` tant que la composition ne l'a pas posé) et l'appelant."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.caller import Caller
from app.features.ide.hashing import file_hash
from app.providers.sandbox.base import CodeSandbox

__all__ = ["IdeContext", "file_hash"]


@dataclass(frozen=True)
class IdeContext:
    db: AsyncSession
    user_id: str
    sandbox: CodeSandbox | None
    caller: Caller
