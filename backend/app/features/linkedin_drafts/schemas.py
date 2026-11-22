from typing import Literal

from pydantic import BaseModel, Field

from app.agents.tools.linkedin_profile import LinkedInClaim, LinkedInText

LinkedInState = Literal["pending", "failed", "ready", "stale"]


class LinkedInStart(BaseModel):
    posting_id: str | None = Field(default=None, min_length=36, max_length=36)


class LinkedInEdit(BaseModel):
    text: LinkedInText
    revision: int = Field(ge=1)


class LinkedInDraftOut(BaseModel):
    id: str
    revision: int
    profile_version: int
    session_id: str
    state: LinkedInState
    text: LinkedInText | None = None
    claims: list[LinkedInClaim] = Field(default_factory=list)
