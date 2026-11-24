from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, Field, computed_field, field_validator

from app.agents.registry import AGENTS
from app.core.clock import DEFAULT_ZONE, Weekday, is_zone
from app.core.domains import normalize_domain
from app.core.validation import KnownMappingKeys
from app.features.settings.delays import validated_delays
from app.providers.llm.base import TIERS, ModelChoice, Tier
from app.providers.llm.model_defaults import DEFAULT_TIERS, supports_vision

HourMinute = Annotated[str, Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")]
SearchProviderName = Literal["searxng", "brave"]
DEFAULT_PROVIDER_ORDER: tuple[SearchProviderName, ...] = ("searxng", "brave")
LanguageCode = Annotated[str, Field(pattern=r"^[a-z]{2}$")]
MAX_DOMAINS = 50
# Starting list (SPEC 10.3, plan 3.6): reference sources first; social networks and
# pages behind a login (SPEC 10.2: never bypassed) excluded.
DEFAULT_PREFERRED_DOMAINS = (
    "wikipedia.org",
    "arxiv.org",
    "github.com",
    "docs.python.org",
    "developer.mozilla.org",
    "pytorch.org",
    "huggingface.co",
    "scikit-learn.org",
)
DEFAULT_EXCLUDED_DOMAINS = (
    "pinterest.com",
    "facebook.com",
    "instagram.com",
    "tiktok.com",
    "linkedin.com",
)


def _no_duplicates[T](values: list[T]) -> list[T]:
    if len(set(values)) != len(values):
        raise ValueError("duplicate value")  # fixed message: the received value is not echoed
    return values


def _domains(values: list[str]) -> list[str]:
    """Normalizes each domain (same rule as the front and the result ranking) and removes
    duplicates; an invalid domain rejects the list, without echoing the input."""
    normalized: list[str] = []
    for value in values:
        domain = normalize_domain(value)
        if domain not in normalized:
            normalized.append(domain)
    return normalized


def _zone(name: str) -> str:
    if not is_zone(name):
        raise ValueError("unknown time zone")  # fixed message: the received value is not echoed
    return name


DomainList = Annotated[list[str], Field(max_length=MAX_DOMAINS), AfterValidator(_domains)]
TimeZoneName = Annotated[str, Field(min_length=1, max_length=64), AfterValidator(_zone)]


class Availability(BaseModel):
    weekday_minutes: int = Field(default=120, ge=0, le=1440)
    weekend_block_min_minutes: int = Field(default=180, ge=0, le=1440)
    weekend_block_max_minutes: int = Field(default=240, ge=0, le=1440)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def weekly_budget_minutes(self) -> int:
        """Weekly budget: five weekdays plus one weekend block (upper bound)."""
        return 5 * self.weekday_minutes + self.weekend_block_max_minutes


class WeeklyReview(BaseModel):
    day: Weekday = "sunday"
    time: HourMinute = "18:00"


DEMO_PREFIX = "demo_"


def is_overridable(name: str) -> bool:
    """True if `name` is an agent of the catalog (P17): in the registry, except demo agents.
    The `PUT`, the read of a stored setting and `GET /settings/agents` agree on it."""
    return name in AGENTS and not name.startswith(DEMO_PREFIX)


class UserSettings(BaseModel):
    availability: Availability = Field(default_factory=lambda: Availability())
    lesson_language: str = "fr"
    search_languages: Annotated[
        list[LanguageCode], Field(min_length=1, max_length=6), AfterValidator(_no_duplicates)
    ] = Field(default_factory=lambda: ["fr", "en"])
    debate_rounds: int = Field(default=3, ge=1, le=5)
    session_token_cap: int = Field(default=300_000, ge=10_000)
    brief_time: HourMinute = "07:00"
    weekly_review: WeeklyReview = Field(default_factory=lambda: WeeklyReview())
    reminder_delays_days: list[int] = Field(default_factory=lambda: [7, 14, 21])
    style_guide: str = ""
    preferred_domains: DomainList = Field(default_factory=lambda: list(DEFAULT_PREFERRED_DOMAINS))
    excluded_domains: DomainList = Field(default_factory=lambda: list(DEFAULT_EXCLUDED_DOMAINS))
    tiers: dict[Tier, ModelChoice] = Field(default_factory=lambda: dict(DEFAULT_TIERS))
    agent_overrides: Annotated[
        dict[str, ModelChoice],
        KnownMappingKeys(frozenset(name for name in AGENTS if is_overridable(name))),
    ] = Field(default_factory=dict)
    search_provider_order: Annotated[
        list[SearchProviderName],
        Field(min_length=1, max_length=2),
        AfterValidator(_no_duplicates),
    ] = Field(default_factory=lambda: list(DEFAULT_PROVIDER_ORDER))
    # Caps of a research session (SPEC 10.4): queries run, pages read.
    search_max_queries: int = Field(default=12, ge=1, le=50)
    search_max_pages: int = Field(default=30, ge=1, le=100)
    # Guided session (SPEC F14): timer work and break cycles, in minutes.
    study_work_minutes: int = Field(default=50, ge=10, le=120)
    study_break_minutes: int = Field(default=10, ge=0, le=60)
    # January's IANA time zone (D98): days, weeks and the Sunday review count in local time.
    timezone: TimeZoneName = DEFAULT_ZONE
    # Market radar (P10, D160): role and area of the last requested run; without a role, the
    # one of the last goal. Personal data: never logged.
    radar_role: str = Field(default="", max_length=120)
    radar_zone: str = Field(default="France", max_length=120)
    # First run done (P20, phase 9): set by the welcome wizard, true by default for
    # settings already stored (migration 0015). The back never sets it back to false.
    onboarding_done: bool = False

    @field_validator("reminder_delays_days")
    @classmethod
    def _valid_delays(cls, delays: list[int]) -> list[int]:
        """Three strictly increasing delays from 1 to 90 days (SPEC 6.2): otherwise the field is
        rejected, and an already stored value falls back to its default (`SettingsService`)."""
        if tuple(delays) != validated_delays(delays):
            raise ValueError("three increasing delays from 1 to 90 days expected")
        return delays

    @field_validator("agent_overrides", mode="before")
    @classmethod
    def _known_agents(cls, overrides: object) -> object:
        """An override only targets a catalog agent (the registry without `demo_*`). Checked
        before reading the values: the received name appears neither in the message nor in the
        error path."""
        if isinstance(overrides, dict) and not all(is_overridable(name) for name in overrides):
            raise ValueError("unknown agent")  # fixed message: the received name is not echoed
        return overrides

    @field_validator("tiers", mode="before")
    @classmethod
    def _known_tiers(cls, tiers: object) -> object:
        """An unknown tier is rejected before reading the values: pydantic would put its key in
        the error path (`tiers.<key>`), hence the input in the response."""
        if isinstance(tiers, dict) and any(name not in TIERS for name in tiers):
            raise ValueError("unknown tier")  # fixed message: the received key is not echoed
        return tiers

    @field_validator("tiers")
    @classmethod
    def _complete_tiers(cls, tiers: dict[Tier, ModelChoice]) -> dict[Tier, ModelChoice]:
        """A missing tier takes its default value back: the factory always finds a model."""
        return {tier: tiers.get(tier, DEFAULT_TIERS[tier]) for tier in TIERS}


class AgentOut(BaseModel):
    """An agent whose model can be chosen (per-agent override, P17) and the tier it follows."""

    name: str
    tier: Tier


class SettingsOut(UserSettings):
    """Settings returned by the API: adds the computed values, never stored."""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def vision_enabled(self) -> bool:
        """False if the `vision` tier points to a model without vision (spec 11.2)."""
        return supports_vision(self.tiers["vision"])

    @classmethod
    def of(cls, settings: UserSettings) -> "SettingsOut":
        return cls.model_validate(settings, from_attributes=True)
