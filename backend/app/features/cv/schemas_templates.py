"""API views of captured CV templates (SPEC 5.2, 14.2, D126).

Each template has a source CV, render images, comparison scores, and render passes.
Only one can be active per user. The font fields describe the free families used
for rendering and their differences from the original.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator

from app.agents.tools.template_grids import zone_code
from app.db.models.career import TemplateStatus

PageKind = Literal["original", "render"]


class TemplateCreated(BaseModel):
    """The newly created template and its capture session."""

    template_id: str
    session_id: str


class TemplateSummaryOut(BaseModel):
    """The current pass's similarity score and the number of completed passes."""

    id: str
    name: str
    status: TemplateStatus
    active: bool
    score: int | None
    passes: int
    page_count: int
    created_at: datetime


class FontUseOut(BaseModel):
    """The free font used for a role and whether it replaced the original font."""

    role: Literal["body", "heading"]
    family: str
    substitute: bool


class ZoneDiffOut(BaseModel):
    """The original and rendered ink coverage in one page region, from 0 to 1."""

    zone: str
    original: float
    render: float

    @field_validator("zone")
    @classmethod
    def _read_zone(cls, value: str) -> str:
        return zone_code(value)


class TemplateOut(TemplateSummaryOut):
    """Template details, capture session, and any failure reason without CV content."""

    selectable: bool
    fonts: list[FontUseOut]
    font_gaps: list[str]
    zones: list[ZoneDiffOut]
    session_id: str | None
    failure_reason: str | None
