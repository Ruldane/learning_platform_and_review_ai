"""What the IDE service operations share: the database session, the owner, the sandbox (`None`
until composition has set it) and the caller."""

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
