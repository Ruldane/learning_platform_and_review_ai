from typing import Literal

from pydantic import BaseModel, Field

from app.db.models.skills import SkillLevel


class GalaxyAction(BaseModel):
    kind: Literal["lesson", "training", "note"]
    ref: str


class GalaxyNode(BaseModel):
    id: str
    kind: Literal["skill", "note"]
    title: str
    domain: str | None = None
    level: SkillLevel | None = None
    gap: int | None = Field(default=None, ge=0)
    action: GalaxyAction


class GalaxyEdge(BaseModel):
    source: str
    target: str
    kind: Literal["prerequisite", "reference", "topic"]


class GalaxyView(BaseModel):
    nodes: list[GalaxyNode]
    edges: list[GalaxyEdge]
    target_label: str | None
