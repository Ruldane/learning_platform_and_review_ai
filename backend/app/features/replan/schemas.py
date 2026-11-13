"""Contrat de la replanification (SPEC F13, D106) : demande de January (« cette semaine je n'ai
que 5 heures »), historique des versions du plan. Les schémas de différence portent leur propre
nom (`VersionDiffOut`, `VersionMoveOut`), mêmes champs que `PlanDiffOut` du programme (F8)."""

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.db.models.program import PlanKind, PlanStatus

# Les valeurs du modèle, jamais recopiées : un statut ajouté plus tard ne ferait pas de 500 sur
# `GET /versions` (relecture 5.9 m6, revue finale de la phase 5). Contrat inchangé.
PlanKindOut = PlanKind
PlanStatusOut = PlanStatus


class ReplanRequest(BaseModel):
    available_minutes: int | None = Field(default=None, ge=60, le=10080)
    message: str | None = Field(default=None, max_length=1000)


class ReplanStarted(BaseModel):
    session_id: str


class VersionMoveOut(BaseModel):
    task: str  # « {module} / {tâche} »
    before: date
    after: date


class VersionDiffOut(BaseModel):
    added: list[str]
    removed: list[str]
    moved: list[VersionMoveOut]
    weeks_before: int
    weeks_after: int


class WeekLoadOut(BaseModel):
    """Charge d'une semaine touchée, avant et après la proposition, et son plafond."""

    rank: int
    start_date: date
    before: int
    after: int
    cap: int


class PlanVersionOut(BaseModel):
    """Une version du plan. `pending` : proposition qui attend January (dans sa session) ;
    `empty` et `impossible` : propositions closes dès leur écriture, jamais à valider."""

    version: int
    kind: PlanKindOut
    status: PlanStatusOut
    reason: str
    created_at: datetime
    accepted_at: datetime | None
    session_id: str | None
    review: str | None  # texte du bilan qui l'a déclenchée
    diff: VersionDiffOut | None
    week_loads: list[WeekLoadOut]
