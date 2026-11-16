"""Schémas des candidatures (SPEC 6, D139). Une 422 nomme les champs (`details.fields`), jamais
leur valeur : entreprise, intitulé, contacts et notes sont des données personnelles. Une 409 de
doublon renvoie les fiches existantes (`AlertOut`), jamais l'entrée."""

from datetime import date, datetime
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

from app.db.models.applications import ApplicationStatus as ApplicationStatus
from app.db.models.applications import Channel, EventKind, ReminderKind
from app.db.models.applications import ReminderStatus as ReminderState

COMPANY_MAX = 200
TITLE_MAX = 200
URL_MAX = 2000
POSTING_TEXT_MAX = 60_000
TEXT_MAX = 2000  # une note du fil
NOTES_MAX = 10_000
LETTER_MAX = 20_000
CONTACTS_MAX = 10
DISTINCT_MAX = 50

AlertLevel = Literal["certain", "probable", "possible", "info"]


def _link(value: str) -> str:
    """Un lien `http` ou `https` avec un hôte ; la valeur n'est jamais citée dans l'erreur."""
    try:
        parts = urlsplit(value)
        ok = parts.scheme.lower() in ("http", "https") and bool(parts.hostname)
    except ValueError:
        ok = False
    if not ok:
        raise ValueError("lien invalide")
    return value


def _text(max_length: int) -> StringConstraints:
    return StringConstraints(strip_whitespace=True, max_length=max_length)


Company = Annotated[str, _text(COMPANY_MAX)]
Title = Annotated[str, _text(TITLE_MAX)]
Link = Annotated[str, _text(URL_MAX), AfterValidator(_link)]
Notes = Annotated[str, _text(NOTES_MAX)]
Id = Annotated[str, Field(min_length=1, max_length=36)]


class ContactIn(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
    role: Annotated[str, _text(120)] | None = None
    url: Annotated[str, _text(500), AfterValidator(_link)] | None = None


class ContactOut(BaseModel):
    id: str
    name: str
    role: str | None
    url: str | None


class ApplicationIn(BaseModel):
    """Création manuelle ou depuis une offre. Avec `posting_id`, l'entreprise, l'intitulé, le
    lien et le texte figé viennent de l'offre (les champs donnés ne servent que si l'offre ne les
    dit pas encore) ; sans `posting_id`, `company` et `title` sont obligatoires (422 `fields`).
    `distinct_from` : les fiches de l'alerte que January a confirmées « autre poste »."""

    posting_id: Id | None = None
    company: Company | None = None
    title: Title | None = None
    url: Link | None = None
    posting_text: Annotated[str, _text(POSTING_TEXT_MAX)] | None = None
    channel: Channel | None = None
    status: ApplicationStatus = "to_apply"
    applied_on: date | None = None
    notes: Notes | None = None
    contacts: list[ContactIn] = Field(default_factory=list, max_length=CONTACTS_MAX)
    distinct_from: list[Id] = Field(default_factory=list, max_length=DISTINCT_MAX)


class IntakeIn(BaseModel):
    """La phrase de January : « j'ai postulé hier chez X pour le poste Y » (1 à 1 000 caractères).
    Une 422 nomme `text`, sans jamais la citer."""

    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


class IntakeOut(BaseModel):
    """La session de l'Assistant de suivi : la fiche en préparation arrive par ses événements
    (`interrupt.requested`, `kind` `application_confirm`)."""

    session_id: str


class ApplicationPatch(BaseModel):
    """Les champs à changer (ceux qui sont envoyés, `null` efface un champ facultatif) ; `contacts`
    remplace la liste. `posting_text` : le texte de l'offre d'une fiche saisie sans lui (il ouvre
    son kit) ; un texte vide l'efface. Le statut ne se change que par
    `POST /applications/{id}/events` : l'envoyer ici est une 422 (`fields: ["status"]`), comme tout
    champ inconnu."""

    model_config = ConfigDict(extra="forbid")

    company: Company | None = None
    title: Title | None = None
    url: Link | None = None
    posting_text: Annotated[str, _text(POSTING_TEXT_MAX)] | None = None
    channel: Channel | None = None
    applied_on: date | None = None
    interview_on: date | None = None
    letter: Annotated[str, _text(LETTER_MAX)] | None = None
    notes: Notes | None = None
    next_action: Annotated[str, _text(200)] | None = None
    next_action_on: date | None = None
    contacts: list[ContactIn] | None = Field(default=None, max_length=CONTACTS_MAX)


class EventIn(BaseModel):
    """Un événement du fil : un changement de statut (`status` obligatoire) ou une note (`text`
    obligatoire). `on` : le jour de l'événement (défaut : aujourd'hui, fuseau de January ; jamais
    plus tard : 422 `on`) ;
    `interview_on` : le jour de l'entretien, pour le statut « Entretien » (défaut : `on`)."""

    kind: Literal["status", "note"]
    status: ApplicationStatus | None = None
    text: Annotated[str, _text(TEXT_MAX)] | None = None
    on: date | None = None
    interview_on: date | None = None


class EventOut(BaseModel):
    id: str
    kind: EventKind
    at: datetime
    status_from: ApplicationStatus | None
    status_to: ApplicationStatus | None
    text: str | None
    ref_id: str | None


ReminderChannel = Literal["linkedin", "email", "none"]
ReminderActionName = Literal["done", "postpone", "ignore"]


class ReminderOut(BaseModel):
    """Une relance : qui contacter, un brouillon prêt à copier (gabarit fixe, aucun LLM), le canal.
    Sans contact : `linkedin_search_url`, la recherche LinkedIn pré remplie (entreprise et poste
    visé). `close_21` : `channel` « none », `draft` est la proposition de classer la fiche."""

    id: str
    application_id: str
    kind: ReminderKind
    due_on: date
    status: ReminderState
    company: str
    title: str
    contact: ContactOut | None
    linkedin_search_url: str | None
    channel: ReminderChannel
    draft: str


class ReminderPatch(BaseModel):
    """Fait, Reporter de 3 jours ou Ignorer ; toute autre valeur est une 422 sans écho."""

    action: ReminderActionName


class AlertOut(BaseModel):
    """Une fiche existante qui ressemble à l'offre entrante : niveau, fiche, message en français
    (date et statut). `info` : simple information, ne bloque rien."""

    level: AlertLevel
    application_id: str
    company: str
    title: str
    status: ApplicationStatus
    applied_on: date | None
    created_on: date
    message: str


class ApplicationRef(BaseModel):
    id: str
    company: str
    title: str
    status: ApplicationStatus
    applied_on: date | None


class ApplicationOut(BaseModel):
    id: str
    posting_id: str | None
    company: str
    title: str
    url: str | None
    channel: Channel | None
    status: ApplicationStatus
    applied_on: date | None
    interview_on: date | None
    cv_version_id: str | None
    cv_version_number: int | None
    next_action: str | None
    next_action_on: date | None
    due_reminders: int
    created_at: datetime
    updated_at: datetime


class ApplicationDetail(ApplicationOut):
    posting_text: str | None
    letter: str | None
    notes: str | None
    contacts: list[ContactOut]
    events: list[EventOut]  # chronologique
    reminders: list[ReminderOut]


class CreatedOut(BaseModel):
    application: ApplicationDetail
    info: list[AlertOut]  # une autre fiche chez la même entreprise dans les 30 jours


class CheckOut(BaseModel):
    """`own` : la fiche de cette offre, si elle existe ; `alerts` : certain, probable, possible ;
    `info` : même entreprise dans les 30 jours."""

    own: ApplicationRef | None
    alerts: list[AlertOut]
    info: list[AlertOut]


class ApplicationStatsOut(BaseModel):
    """Les indicateurs (SPEC 6.4) ; `StatsOut` est déjà le nom des statistiques de la mémoire."""

    by_status: dict[ApplicationStatus, int]
    response_rate: float | None
    mean_response_days: float | None
    due_reminders: int
