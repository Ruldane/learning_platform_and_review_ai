"""Ce que les opérations du service de l'IDE partagent : la session de base de données, la
propriétaire, le bac à sable (`None` tant que la composition ne l'a pas posé) et l'appelant."""

import hashlib
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.caller import Caller
from app.providers.sandbox.base import CodeSandbox


@dataclass(frozen=True)
class IdeContext:
    db: AsyncSession
    user_id: str
    sandbox: CodeSandbox | None
    caller: Caller


def file_hash(content: str) -> str:
    """L'empreinte d'un fichier (P9) : sha256 hexadécimal, en minuscules, du contenu en UTF-8."""
    return hashlib.sha256(content.encode()).hexdigest()
