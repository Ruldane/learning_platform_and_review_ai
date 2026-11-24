"""HTTP dependencies shared across the IDE routes."""

from typing import Annotated

from fastapi import Depends, Path
from starlette.requests import HTTPConnection

from app.core.caller import CallerDep
from app.core.deps import CurrentUserDep, Db
from app.features.ide.service import IdeService


def get_ide_service(
    conn: HTTPConnection, current: CurrentUserDep, db: Db, caller: CallerDep
) -> IdeService:
    return IdeService(db, current.id, conn.app.state.providers.sandbox, caller)


Id = Annotated[str, Path(min_length=1, max_length=36)]
Ide = Annotated[IdeService, Depends(get_ide_service)]
