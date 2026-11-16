"""Contrat du brief du jour (SPEC 14.2, P11, P12, D162). Un instantané : les rubriques calculées
par le code (bloc, révisions, relances, offres, semaine) sont figées à la création ; la ressource
et le conseil arrivent ensuite, écrits par les agents. Chaque rubrique mène à l'écran vivant."""

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.db.models.applications import ReminderKind
from app.db.models.daily import AdviceStatus, BriefOrigin


class BriefBlockTask(BaseModel):
    title: str
    minutes: int


class BlockRubric(BaseModel):
    """Le bloc d'étude du jour : la leçon et ses tâches dues (`minutes` : leur total)."""

    module_title: str
    lesson_id: str
    lesson_title: str
    minutes: int
    tasks: list[BriefBlockTask]


class ReviewsRubric(BaseModel):
    """`queue` : les fiches de la file du jour ; `remaining` : celles dues au-delà de la file."""

    queue: int
    remaining: int


class ReminderItem(BaseModel):
    reminder_id: str
    application_id: str
    company: str
    title: str
    kind: ReminderKind
    due_on: date


class RemindersRubric(BaseModel):
    """`due` : toutes les relances dues ; `items` : les 5 premières."""

    due: int
    items: list[ReminderItem]


class OfferItem(BaseModel):
    url: str
    title: str | None
    company: str | None
    score: int


class OffersRubric(BaseModel):
    """Les nouvelles offres du radar (score au moins 70), 5 au plus ; `run_id` : le relevé de la
    meilleure (`None` sans offre)."""

    run_id: str | None
    items: list[OfferItem]


class WeekRubric(BaseModel):
    """L'avancement de la semaine locale du programme validé le plus récent."""

    planned_minutes: int
    done_minutes: int
    tasks_done: int
    tasks_total: int
    study_minutes: int
    streak_days: int


class BriefResourceOut(BaseModel):
    """La ressource du jour : un résultat réel du web dont la page a été lue. `published` : sa date
    si le web la donne, jamais devinée."""

    title: str
    url: str
    domain: str
    published: str | None
    why: str


class BriefOut(BaseModel):
    """Le brief d'un jour local. `advice_status` : `pending` tant que la session du conseil vit
    (le seul état qui change encore) ; `ready` (`advice` rangé) ; `failed` (conseil impossible ou
    session morte) et `unavailable` (aucun modèle) sont **définitifs pour la journée** : le
    conseil n'est jamais relancé, aucun « Réessayer » à offrir."""

    id: str
    day: date
    origin: BriefOrigin
    generated_at: datetime
    block: BlockRubric | None
    reviews: ReviewsRubric
    reminders: RemindersRubric
    offers: OffersRubric
    week: WeekRubric | None
    resource: BriefResourceOut | None
    unavailable: list[str] = Field(
        default_factory=list,
        description="Les rubriques dont la source était en panne à la création (vides ce jour).",
    )
    advice: list[str] | None
    advice_status: AdviceStatus = Field(
        description="`pending` change encore ; `ready`, `failed` et `unavailable` sont définitifs."
    )
    session_id: str | None
