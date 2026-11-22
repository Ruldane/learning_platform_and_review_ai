from typing import Annotated, Literal

from pydantic import BaseModel, StringConstraints

from app.agents.tools.code_trial_port import CodePleading

Choice = Literal["prosecutor", "defender", "compromise"]
TrialStatus = Literal["running", "ready", "decided", "failed"]


class TrialOpened(BaseModel):
    trial_id: str
    session_id: str


class TrialVerdict(BaseModel):
    choice: Choice
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=8, max_length=2000)]


class TrialView(BaseModel):
    id: str
    session_id: str
    title: str
    files_version: int
    current: bool
    file_count: int
    status: TrialStatus
    pleadings: list[CodePleading]
    verdict: TrialVerdict | None
