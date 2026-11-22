from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, StringConstraints

GithubSha = Annotated[str, StringConstraints(pattern=r"^[a-fA-F0-9]{40}$", to_lower=True)]


class GithubClaimIn(BaseModel):
    repo_url: str = Field(min_length=1, max_length=200)
    sha: GithubSha


class GithubClaimOut(BaseModel):
    id: UUID
    profile_url: HttpUrl
    code: str
    expires_at: datetime


class GithubProofOut(BaseModel):
    commit_url: HttpUrl
    sha: GithubSha
    verified_at: datetime
