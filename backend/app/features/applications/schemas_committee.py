"""Schémas du comité de recrutement simulé (SPEC F19, D147). Une 422 nomme les champs
(`details.fields`), jamais leur valeur : le CV et les paroles du comité sont des données
personnelles.

`status` : `running` (en cours), `done` (verdict rangé), `failed` (la session s'est terminée sans
résultat). `previous` : l'avant et l'après, `None` sans exécution terminée plus ancienne sur la
même offre, ou tant que celle-ci n'est pas terminée. C'est une simulation, jamais une prédiction."""

from datetime import datetime

from pydantic import BaseModel

from app.agents.tools.committee_schema import Persona, Verdict
from app.db.models.applications import RunStatus as RunStatus
from app.features.applications.schemas import Id


class CommitteeIn(BaseModel):
    """La version de CV à faire juger : elle doit être prête (PDF rendu)."""

    cv_version_id: Id


class CommitteeStartOut(BaseModel):
    run_id: str
    session_id: str


class VoteOut(BaseModel):
    """Le vote d'une persona : oui, non ou peut-être, son objection principale, sa raison."""

    persona: Persona
    vote: Verdict
    objection: str
    reason: str


class ObjectionOut(BaseModel):
    """Une objection du comité (la plus lourde d'abord) et les personas qui la portent."""

    text: str
    personas: list[Persona]


class ChangeOut(BaseModel):
    """Un des trois changements qui feraient basculer un vote : la persona visée, les faits du
    profil à mettre en avant. `needs_skill` : il demande un terme que le profil ne dit pas
    (`terms`), une compétence « à acquérir », jamais à écrire dans le CV telle quelle."""

    text: str
    persona: Persona
    fact_ids: list[str]
    needs_skill: bool
    terms: list[str]


class VoteChange(BaseModel):
    """Le vote d'une persona avant (exécution précédente) et après (celle-ci)."""

    persona: Persona
    before: Verdict
    after: Verdict


class CommitteeDiff(BaseModel):
    """L'avant et l'après (F19) : les votes, les objections disparues (`objections_resolved`) et les
    nouvelles (`objections_new`) par rapport à l'exécution `previous_id`."""

    previous_id: str
    votes: list[VoteChange]
    objections_resolved: list[str]
    objections_new: list[str]


class CommitteeRunOut(BaseModel):
    """Une exécution du comité. `votes`, `objections` et `changes` sont vides tant qu'elle n'est
    pas terminée ; `verdict` est la majorité des quatre votes (égalité : peut-être)."""

    id: str
    cv_version_id: str
    posting_id: str
    application_id: str | None
    session_id: str
    status: RunStatus
    votes: list[VoteOut]
    verdict: Verdict | None
    objections: list[ObjectionOut]
    changes: list[ChangeOut]
    previous: CommitteeDiff | None
    created_at: datetime
