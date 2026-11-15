"""Port de la création d'une fiche en une phrase (SPEC 6.1, 6.3, D141). `app.agents` n'importe
aucune feature (contrat 6) : il décrit ici ce dont le parcours `application_intake` a besoin (le
jour de January, les alertes de doublon d'une fiche en préparation, la création) ; la feature
`applications` l'implémente (`AgentApplicationStore`, `service/agent_store.py`).

La phrase de January et la fiche qu'elle décrit sont des données personnelles : ni ici ni dans
l'implémentation elles ne sont journalisées (17.2).

- `intake_alerts` : mêmes règles que la création à la main (`match`, 7.1), **sans** les simples
  informations (« même entreprise dans les 30 jours ») qui ne bloquent rien ; les fiches sont
  rendues de la plus forte alerte à la plus faible.
- `save_intake` : la création passe par le service de la route `POST /applications` (même contrôle
  des doublons : sans `distinct_from` qui les couvre, une fiche qui ressemble est refusée) et
  **idempotente par session** : un nœud rejoué après un arrêt (SPEC 9.4) ne crée pas de seconde
  fiche, il relit l'identifiant de celle de la session.
"""

from dataclasses import dataclass
from datetime import date
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.errors import AppError
from app.db.models.applications import ApplicationStatus, Channel

AlertStrength = Literal["certain", "probable", "possible"]
COMPANY_MAX = 200
TITLE_MAX = 200
CONTACT_MAX = 120
NOTES_MAX = 500


class IntakeDraft(BaseModel):
    """La fiche que décrit la phrase de January : sortie structurée de l'Assistant de suivi, puis
    ce que January confirme. Un champ facultatif vide vaut « absent » ; rien n'est inventé."""

    model_config = ConfigDict(str_strip_whitespace=True)

    company: str = Field(min_length=1, max_length=COMPANY_MAX)
    title: str = Field(min_length=1, max_length=TITLE_MAX)
    status: ApplicationStatus = "applied"
    applied_on: date | None = None  # « hier » résolu par rapport au jour de January
    channel: Channel | None = None
    contact_name: str | None = Field(default=None, max_length=CONTACT_MAX)
    contact_role: str | None = Field(default=None, max_length=CONTACT_MAX)
    notes: str | None = Field(default=None, max_length=NOTES_MAX)

    @model_validator(mode="after")
    def _planned_has_no_date(self) -> "IntakeDraft":
        """Une candidature « à postuler » n'a pas encore de jour d'envoi."""
        if self.status == "to_apply":
            self.applied_on = None
        return self

    @field_validator(
        "applied_on", "channel", "contact_name", "contact_role", "notes", mode="before"
    )
    @classmethod
    def _blank_is_absent(cls, value: Any) -> Any:
        return None if isinstance(value, str) and not value.strip() else value


@dataclass(frozen=True)
class IntakeContext:
    """Le jour de January (son fuseau) et la langue de son interface."""

    today: date
    language: str


@dataclass(frozen=True)
class AlertView:
    """Une fiche existante qui ressemble à la fiche en préparation : sa force, son identifiant et
    le message en français (date et statut, SPEC 6.3)."""

    level: AlertStrength
    application_id: str
    message: str


class ApplicationStore(Protocol):
    async def intake_context(self, user_id: str) -> IntakeContext:
        """Le jour de January (fuseau de ses réglages) et la langue de son interface."""
        ...

    async def intake_alerts(self, user_id: str, draft: IntakeDraft) -> list[AlertView]:
        """Les fiches qui bloquent la création (voir le module), la plus forte d'abord."""
        ...

    async def save_intake(
        self, user_id: str, session_id: str, draft: IntakeDraft, distinct_from: list[str]
    ) -> str:
        """Crée la fiche et rend son identifiant ; idempotent par session. `distinct_from` : les
        fiches de l'alerte que January a confirmées « autre poste » ; 409 `application_duplicate`
        si une fiche qui ressemble n'est pas couverte."""
        ...


def applications_unavailable() -> AppError:
    return AppError(
        "applications_unavailable", "Les candidatures ne sont pas branchées sur ce moteur.", 503
    )


class _NoApplications:
    """Valeur par défaut du moteur (tests, démarrages sans la feature)."""

    async def intake_context(self, user_id: str) -> IntakeContext:
        raise applications_unavailable()

    async def intake_alerts(self, user_id: str, draft: IntakeDraft) -> list[AlertView]:
        raise applications_unavailable()

    async def save_intake(
        self, user_id: str, session_id: str, draft: IntakeDraft, distinct_from: list[str]
    ) -> str:
        raise applications_unavailable()


NO_APPLICATIONS: ApplicationStore = _NoApplications()
