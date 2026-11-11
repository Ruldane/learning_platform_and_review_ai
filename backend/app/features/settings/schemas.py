from typing import Annotated, Literal

from pydantic import BaseModel, Field, computed_field, field_validator

from app.providers.llm.base import TIERS, ModelChoice, Tier
from app.providers.llm.model_defaults import DEFAULT_TIERS, supports_vision

HourMinute = Annotated[str, Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")]
Weekday = Literal["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


class Availability(BaseModel):
    weekday_minutes: int = Field(default=120, ge=0, le=1440)
    weekend_block_min_minutes: int = Field(default=180, ge=0, le=1440)
    weekend_block_max_minutes: int = Field(default=240, ge=0, le=1440)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def weekly_budget_minutes(self) -> int:
        """Budget hebdomadaire : cinq jours de semaine plus un bloc de week-end (borne haute)."""
        return 5 * self.weekday_minutes + self.weekend_block_max_minutes


class WeeklyReview(BaseModel):
    day: Weekday = "sunday"
    time: HourMinute = "18:00"


class UserSettings(BaseModel):
    availability: Availability = Field(default_factory=lambda: Availability())
    lesson_language: str = "fr"
    search_languages: list[str] = Field(default_factory=lambda: ["fr", "en"])
    debate_rounds: int = Field(default=3, ge=1, le=5)
    session_token_cap: int = Field(default=300_000, ge=10_000)
    brief_time: HourMinute = "07:00"
    weekly_review: WeeklyReview = Field(default_factory=lambda: WeeklyReview())
    reminder_delays_days: list[int] = Field(default_factory=lambda: [7, 14, 21])
    style_guide: str = ""
    preferred_domains: list[str] = Field(default_factory=list)
    excluded_domains: list[str] = Field(default_factory=list)
    tiers: dict[Tier, ModelChoice] = Field(default_factory=lambda: dict(DEFAULT_TIERS))
    agent_overrides: dict[str, ModelChoice] = Field(default_factory=dict)
    search_provider_order: list[str] = Field(default_factory=lambda: ["searxng", "brave"])

    @field_validator("tiers")
    @classmethod
    def _complete_tiers(cls, tiers: dict[Tier, ModelChoice]) -> dict[Tier, ModelChoice]:
        """Un niveau absent reprend sa valeur par défaut : la fabrique trouve toujours un modèle."""
        return {tier: tiers.get(tier, DEFAULT_TIERS[tier]) for tier in TIERS}


class SettingsOut(UserSettings):
    """Réglages renvoyés par l'API : ajoute les valeurs calculées, jamais stockées."""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def vision_enabled(self) -> bool:
        """Faux si le niveau `vision` pointe vers un modèle sans vision (spec 11.2)."""
        return supports_vision(self.tiers["vision"])

    @classmethod
    def of(cls, settings: UserSettings) -> "SettingsOut":
        return cls.model_validate(settings, from_attributes=True)
