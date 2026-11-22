"""Le second lecteur ne reçoit que la remise et le critère contesté."""

from dataclasses import dataclass
from typing import Annotated, Protocol

from pydantic import BaseModel, StringConstraints

APPEAL_GRAPH = "grade_appeals"


class AppealReading(BaseModel):
    met: bool
    comment: Annotated[str, StringConstraints(strip_whitespace=True, min_length=4, max_length=1800)]


@dataclass(frozen=True)
class AppealContext:
    criterion: str
    submission: str
    reason: str
    complete: bool


class GradeAppealsStore(Protocol):
    async def context(self, user_id: str, appeal_id: str, session_id: str) -> AppealContext: ...

    async def save(
        self, user_id: str, appeal_id: str, session_id: str, reading: AppealReading
    ) -> None: ...


class _MissingAppeals:
    async def context(self, user_id: str, appeal_id: str, session_id: str) -> AppealContext:
        raise RuntimeError("La seconde lecture n’est pas branchée.")

    async def save(
        self, user_id: str, appeal_id: str, session_id: str, reading: AppealReading
    ) -> None:
        raise RuntimeError("La seconde lecture n’est pas branchée.")


NO_APPEALS: GradeAppealsStore = _MissingAppeals()
