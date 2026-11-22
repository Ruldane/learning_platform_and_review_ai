from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

CandidateKind = Literal["profile", "skill", "project", "github", "linkedin"]
LinkTarget = Literal["cv", "kit"]


class Candidate(BaseModel):
    id: str
    kind: CandidateKind
    label: str
    text: str
    url: str | None = None


class SelectDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    selected: list[Annotated[str, StringConstraints(min_length=1, max_length=160)]] = Field(
        min_length=1, max_length=50
    )


class PortfolioDraftOut(BaseModel):
    id: UUID
    digest: str
    destination: str | None
    created_at: datetime


class WithdrawalApproval(BaseModel):
    model_config = ConfigDict(extra="forbid")

    draft_id: UUID
    destination: Annotated[str, Field(min_length=1, max_length=300)]
    confirmed: Literal[True]


class PublicationApproval(WithdrawalApproval):
    digest: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class PublicationOut(BaseModel):
    revision_id: UUID
    url: str
    published_at: datetime
    available: bool
    use_in_cv: bool
    use_in_kit: bool


class LinkChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revision_id: UUID
    url: Annotated[str, Field(min_length=1, max_length=300)]
    enabled: bool


class SiteOut(BaseModel):
    candidates: list[Candidate]
    draft: PortfolioDraftOut | None
    publication: PublicationOut | None
