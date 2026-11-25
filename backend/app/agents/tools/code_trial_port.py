"""Port de lecture du projet figé et de dépôt des deux plaidoiries."""

from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, Field, StrictInt, StringConstraints

from app.core.errors import AppError

GRAPH = "code_trial"
PROSECUTOR = "code_prosecutor"
DEFENDER = "code_defender"
TrialRole = Literal["prosecutor", "defender"]


class CodePassage(BaseModel):
    path: str
    start_line: int
    end_line: int
    text: str


class CodeArgument(BaseModel):
    argument: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2800)
    ]
    references: list[StrictInt] = Field(min_length=1, max_length=8)


class CodePleading(BaseModel):
    role: TrialRole
    argument: str
    citations: list[CodePassage]


class CodeTrialPort(Protocol):
    async def passages(self, user_id: str, session_id: str, trial_id: str) -> list[CodePassage]: ...

    async def save(
        self, user_id: str, session_id: str, trial_id: str, pleadings: list[CodePleading]
    ) -> None: ...


class _Unavailable:
    async def passages(self, user_id: str, session_id: str, trial_id: str) -> list[CodePassage]:
        raise AppError("code_trial_unavailable", "The code trial is unavailable.", 503)

    async def save(
        self, user_id: str, session_id: str, trial_id: str, pleadings: list[CodePleading]
    ) -> None:
        raise AppError("code_trial_unavailable", "The code trial is unavailable.", 503)


NO_CODE_TRIAL: CodeTrialPort = _Unavailable()
