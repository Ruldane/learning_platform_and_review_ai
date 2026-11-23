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
# Liste de départ (SPEC 10.3, plan 3.6) : sources de référence en tête ; réseaux sociaux et
# pages derrière une connexion (SPEC 10.2 : jamais contournées) exclus.
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
        raise ValueError("valeur en double")  # message fixe : la valeur reçue n'est pas recopiée
    return values


def _domains(values: list[str]) -> list[str]:
    """Normalise chaque domaine (même règle que le front et le classement des résultats) et
    retire les doublons ; un domaine invalide refuse la liste, sans recopier la saisie."""
    normalized: list[str] = []
    for value in values:
        domain = normalize_domain(value)
        if domain not in normalized:
            normalized.append(domain)
    return normalized


def _zone(name: str) -> str:
    if not is_zone(name):
        raise ValueError("fuseau inconnu")  # message fixe : la valeur reçue n'est pas recopiée
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
        """Budget hebdomadaire : cinq jours de semaine plus un bloc de week-end (borne haute)."""
        return 5 * self.weekday_minutes + self.weekend_block_max_minutes


class WeeklyReview(BaseModel):
    day: Weekday = "sunday"
    time: HourMinute = "18:00"


DEMO_PREFIX = "demo_"


def is_overridable(name: str) -> bool:
    """Vrai si `name` est un agent du catalogue (P17) : au registre, hors agents de démonstration.
    Le `PUT`, la lecture d'un réglage stocké et `GET /settings/agents` s'accordent sur lui."""
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
    # Plafonds d'une session de recherche (SPEC 10.4) : requêtes lancées, pages lues.
    search_max_queries: int = Field(default=12, ge=1, le=50)
    search_max_pages: int = Field(default=30, ge=1, le=100)
    # Session guidée (SPEC F14) : cycles de travail et de pause du minuteur, en minutes.
    study_work_minutes: int = Field(default=50, ge=10, le=120)
    study_break_minutes: int = Field(default=10, ge=0, le=60)
    # Fuseau IANA de January (D98) : jours, semaines et bilan du dimanche se comptent en local.
    timezone: TimeZoneName = DEFAULT_ZONE
    # Radar du marché (P10, D160) : poste et zone du dernier relevé demandé ; sans poste, celui du
    # dernier objectif. Données personnelles : jamais journalisées.
    radar_role: str = Field(default="", max_length=120)
    radar_zone: str = Field(default="France", max_length=120)
    # Premier lancement fini (P20, phase 9) : posé par l'assistant d'accueil, vrai d'office pour les
    # réglages déjà stockés (migration 0015). Le back ne le remet jamais à faux.
    onboarding_done: bool = False

    @field_validator("reminder_delays_days")
    @classmethod
    def _valid_delays(cls, delays: list[int]) -> list[int]:
        """Trois délais strictement croissants de 1 à 90 jours (SPEC 6.2) : sinon le champ est
        refusé, et une valeur déjà stockée retombe sur son défaut (`SettingsService`)."""
        if tuple(delays) != validated_delays(delays):
            raise ValueError("trois délais croissants de 1 à 90 jours attendus")
        return delays

    @field_validator("agent_overrides", mode="before")
    @classmethod
    def _known_agents(cls, overrides: object) -> object:
        """Une surcharge ne vise qu'un agent du catalogue (le registre sans `demo_*`). Contrôlé
        avant la lecture des valeurs : le nom reçu n'apparaît ni dans le message ni dans le chemin
        de l'erreur."""
        if isinstance(overrides, dict) and not all(is_overridable(name) for name in overrides):
            raise ValueError("agent inconnu")  # message fixe : le nom reçu n'est pas recopié
        return overrides

    @field_validator("tiers", mode="before")
    @classmethod
    def _known_tiers(cls, tiers: object) -> object:
        """Un niveau inconnu est refusé avant la lecture des valeurs : pydantic mettrait sa clé
        dans le chemin de l'erreur (`tiers.<clé>`), donc la saisie dans la réponse."""
        if isinstance(tiers, dict) and any(name not in TIERS for name in tiers):
            raise ValueError("niveau inconnu")  # message fixe : la clé reçue n'est pas recopiée
        return tiers

    @field_validator("tiers")
    @classmethod
    def _complete_tiers(cls, tiers: dict[Tier, ModelChoice]) -> dict[Tier, ModelChoice]:
        """Un niveau absent reprend sa valeur par défaut : la fabrique trouve toujours un modèle."""
        return {tier: tiers.get(tier, DEFAULT_TIERS[tier]) for tier in TIERS}


class AgentOut(BaseModel):
    """Un agent dont le modèle se choisit (surcharge par agent, P17) et le niveau qu'il suit."""

    name: str
    tier: Tier


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
