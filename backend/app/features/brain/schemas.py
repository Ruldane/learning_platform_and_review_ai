"""Schémas de gestion et de synchronisation des dossiers Cerveau."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

FolderName = Annotated[str, Field(min_length=1, max_length=200)]
FolderPath = Annotated[str, Field(min_length=1, max_length=2048)]
RelativePath = Annotated[str, Field(min_length=1, max_length=2048)]
Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
Count = Annotated[int, Field(ge=0, le=2**31 - 1)]


class FolderIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: FolderName
    path: FolderPath
    paused: bool = False


class FolderPatch(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: FolderName | None = None
    path: FolderPath | None = None
    paused: bool | None = None


class FolderSummary(BaseModel):
    id: str
    name: str
    paused: bool
    revision: int


class FolderOut(FolderSummary):
    model_config = ConfigDict(from_attributes=True)

    path: str


class IgnoredCounts(BaseModel):
    technical: Count = 0
    link: Count = 0
    extension: Count = 0
    binary: Count = 0
    too_large: Count = Field(default=0, alias="tooLarge")
    path: Count = 0
    special: Count = 0
    unreadable: Count = 0
    changed: Count = 0


class ReportIn(BaseModel):
    state: Literal["syncing", "done", "incomplete"]
    scanned: Count
    added: Count
    changed: Count
    removed: Count
    ignored: IgnoredCounts
    errors: Count


class ReportOut(ReportIn):
    reported_at: datetime


class FolderStatus(FolderSummary):
    total: Count
    queued: Count
    processing: Count
    indexed: Count
    error: Count
    report: ReportOut | None


class SyncTokenOut(BaseModel):
    token: str


class FileOut(BaseModel):
    path: str
    size: int
    sha256: str
    document_id: str
    status: Literal["queued", "processing", "indexed", "error"]


class InventoryOut(BaseModel):
    files: list[FileOut]


class RemoveIn(BaseModel):
    path: RelativePath
