from datetime import datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Digest = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class ProofPacketReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mission_id: UUID
    proof_id: UUID
    revision: int = Field(strict=True, ge=0)


class ProofPacketSource(ProofPacketReference):
    title: str


class ProofPacketSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Title
    sources: list[ProofPacketReference] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def unique_sources(self) -> Self:
        if len({source.mission_id for source in self.sources}) != len(self.sources):
            raise ValueError("Select distinct submissions.")
        return self


class ProofPacketCreate(ProofPacketSelection):
    expected_digest: Digest


class ProofPacketMeasure(BaseModel):
    index: int
    label: str
    observed: int
    target: int


class ProofPacketItem(ProofPacketSource):
    recorded_at: datetime
    artifact: str
    artifact_digest: Digest
    measurements: list[ProofPacketMeasure]


class ProofPacketManifest(BaseModel):
    schema_version: Literal[1] = 1
    title: str
    proofs: list[ProofPacketItem]
    procedure: list[str]


class ProofPacketPreview(BaseModel):
    manifest: ProofPacketManifest
    digest: Digest


class ProofPacketOut(ProofPacketPreview):
    id: UUID
    created_at: datetime


class ProofPacketSummary(BaseModel):
    id: UUID
    title: str
    created_at: datetime
