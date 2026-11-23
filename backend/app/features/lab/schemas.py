from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.features.lab.navigation import PINNABLE

TourState = Literal["pending", "done", "disabled"]


class LabPreferences(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pinned: list[str] = Field(default_factory=list)
    tour: TourState = "pending"


class LabPreferencesPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pinned: list[str] | None = Field(default=None, max_length=len(PINNABLE))
    tour: TourState | None = None

    @field_validator("pinned")
    @classmethod
    def valid_pins(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return None
        if len(values) != len(set(values)) or any(value not in PINNABLE for value in values):
            raise ValueError("Sélectionne des activités distinctes du Labo.")
        return values
