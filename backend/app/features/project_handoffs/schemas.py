from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints

Commands = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1_500)]
Notes = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4_000)]
Digest = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class ProjectHandoffSource(BaseModel):
    project_id: UUID
    project_title: str
    submitted_at: datetime
    description: str | None
    repo_url: str | None


class ProjectHandoffDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    commands: Commands
    limitations: Notes
    steps: Notes


class ProjectHandoffApproval(ProjectHandoffDraft):
    expected_digest: Digest
    approved: Literal[True]


class ProjectHandoffPreview(BaseModel):
    digest: Digest
    markdown: str


class ProjectHandoffSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    project_title: str
    submitted_at: datetime
    created_at: datetime
    digest: Digest


class ProjectHandoffOut(ProjectHandoffSummary):
    markdown: str
