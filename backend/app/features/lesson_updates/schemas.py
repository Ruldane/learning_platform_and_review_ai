from typing import Literal

from pydantic import BaseModel

UpdateState = Literal["preparing", "ready", "stale", "failed", "checking", "published"]


class UpdateChange(BaseModel):
    block: int
    before: str
    after: str


class UpdateView(BaseModel):
    id: str
    library: str
    version: str
    source_url: str
    apis: list[str]
    state: UpdateState
    explanation: str | None = None
    changes: list[UpdateChange]
    preparation_session_id: str
    publication_session_id: str | None = None


class UpdateAccepted(BaseModel):
    session_id: str
