from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.features.proof_packets.service import ProofPacketManifest

ShareStatus = Literal["active", "expired", "revoked"]


class MentorShareCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    packet_id: UUID
    expected_digest: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
    valid_hours: int = Field(strict=True, ge=1, le=168)
    confirmed: Literal[True]


class MentorShareOut(BaseModel):
    id: UUID
    packet_id: UUID
    title: str
    digest: str
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None
    status: ShareStatus


class MentorShareIssued(BaseModel):
    share: MentorShareOut
    token: str


class MentorCommentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proof_id: UUID
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class MentorCommentOut(BaseModel):
    id: UUID
    proof_id: UUID
    text: str
    created_at: datetime


class MentorOwnedComment(MentorCommentOut):
    reviewed: bool


class MentorCommentReview(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    reviewed: bool


class MentorShareDetail(MentorShareOut):
    comments: list[MentorOwnedComment]


class MentorSharedWork(BaseModel):
    manifest: ProofPacketManifest
    digest: str
    expires_at: datetime
