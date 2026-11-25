"""Master profile schemas (SPEC 5.1, 14.2; D124). A 422 never copies the input back: on the
profile routes, `details.fields` names the fields by their path ("experiences.2.role")."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.agents.tools.cv_schema import MasterProfileData
from app.db.models.career import ProfileOrigin, ProfileStatus


class ProfileOut(BaseModel):
    """A profile version. `source`: `archivist` (draft taken from the documents) or `january`
    (version she validated). `dropped`: lines removed from the draft (figure or fact not found
    in the documents, invisible text), shown to January only."""

    version: int
    status: ProfileStatus
    data: MasterProfileData
    source: ProfileOrigin
    created_at: datetime
    dropped: list[str]


class ProfileStateOut(BaseModel):
    """`draft`: only if it is more recent than the validated version. `session_id`: profile
    capture in progress (to follow through its events), otherwise `None`. `source_document_id`:
    the CV (PDF labelled `cv`) of the last profile import, if it is still in memory, otherwise
    `None` ("Use my profile CV" to capture a template)."""

    validated: ProfileOut | None
    draft: ProfileOut | None
    session_id: str | None
    source_document_id: str | None


class ProfilePutIn(BaseModel):
    """`base_version`: the version January has read (the latest, otherwise 409
    `profile_conflict`); `None` if no version exists yet."""

    data: MasterProfileData
    base_version: int | None = Field(default=None, ge=1)


class ProfileVersionOut(BaseModel):
    version: int
    status: ProfileStatus
    source: ProfileOrigin
    created_at: datetime


class ProfileImportStarted(BaseModel):
    """Profile capture started: the `cv_capture` session and the documents stored in memory
    (CV first, then LinkedIn)."""

    session_id: str
    document_ids: list[str]
