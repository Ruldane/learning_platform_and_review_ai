"""Port de la replanification (SPEC F13, D105). `app.agents` n'importe aucune feature (contrat 6) :
il décrit ici ce dont le parcours `replan` a besoin (le bilan, le plan à faire par références, le
rangement d'une proposition, son acceptation ou son refus) ; la feature `replan` l'implémente
(tâche 5.9).

Le Stratège ne réécrit pas le plan : il **retire** des tâches et en **ajoute** par référence
(`t12`, `m3`) ; le code range tout le reste (85 %, pratique, quiz, débordement en semaines
« Suite »). Les identifiants réels (`task_id`, `module_id`) ne sont jamais montrés au modèle
(F7) : le parcours garde l'instantané du contexte dans son état et passe au port la table
« référence → id » de cet instantané (`refs`).

Chaque écriture est idempotente : `preview` par `(session, revision)`, `apply` et `refuse` par
version ; un nœud rejoué après un arrêt (SPEC 9.4) relit la même chose, jamais une ligne de plus.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Annotated, Protocol

from pydantic import BaseModel, Field

from app.agents.runtime.prose import Prose
from app.agents.tools.program_port import BudgetView
from app.agents.tools.study_schema import ReplanOption, ReplanTrigger, ReviewState
from app.core.errors import AppError
from app.db.models.program import TaskType

WEEK_CAP_PERCENT = 85
TASK_REF = r"^t\d{1,4}$"
MODULE_REF = r"^m\d{1,3}$"


def week_cap(available_minutes: int) -> int:
    """Plafond de la semaine en cours quand January n'a que `available_minutes` : 85 %, arrondi
    vers le bas, en entiers (en flottants, `0.85 * 300` vaut 254,99… ; ici 255)."""
    return available_minutes * WEEK_CAP_PERCENT // 100


@dataclass(frozen=True)
class ModuleRef:
    ref: str  # « m3 » : la seule référence montrée au modèle
    title: str
    skills: list[str]
    module_id: str  # jamais rendu au modèle (F7)


@dataclass(frozen=True)
class TaskRef:
    """Une tâche à faire (de la semaine en cours et des suivantes, retards compris)."""

    ref: str  # « t12 »
    title: str
    type: TaskType
    minutes: int
    planned_date: date
    module_ref: str
    late: bool  # datée avant aujourd'hui et pas faite
    task_id: str  # jamais rendu au modèle (F7)


@dataclass(frozen=True)
class ReviewView:
    """Le bilan hebdomadaire qui a déclenché la replanification (texte écrit par le code)."""

    entry_id: str
    week_start: date
    text: str
    state: ReviewState
    late_ratio: float


@dataclass(frozen=True)
class ReplanContext:
    program_id: str
    title: str
    goal: str
    deadline: date | None
    budget: BudgetView
    review: ReviewView | None
    options: tuple[ReplanOption, ...]  # vide : rien à décider
    modules: list[ModuleRef]
    tasks: list[TaskRef]  # à faire, de la semaine en cours et des suivantes, retards compris
    week_cap_override: int | None  # `week_cap(minutes disponibles cette semaine)`, si données
    message: str | None  # texte de January (« je n'ai que 5 heures… ») : une note du Stratège

    def refs(self) -> dict[str, str]:
        """Référence (`t12`, `m3`) → id réel, sur cet instantané."""
        found = {m.ref: m.module_id for m in self.modules}
        found.update({t.ref: t.task_id for t in self.tasks})
        return found


# --- Sortie structurée du Stratège --------------------------------------------------------------
# Une classe par droit (D105 (2)) : le modèle ne reçoit que le schéma de ce qu'il a le droit de
# faire. Résumé et critère de fin sont du texte lu (`Prose`) ; références et titres restent
# refusés s'ils sont mal formés (re-demandés par `structured_call`).


class ReplanTaskDraft(BaseModel):
    module: str = Field(pattern=MODULE_REF)
    title: str = Field(min_length=3, max_length=120)
    type: TaskType
    minutes: int = Field(ge=15, le=120)
    done_criterion: Prose = Field(min_length=3, max_length=200)


class ReplanSummary(BaseModel):
    """Sans option, avec « repousser » ou « avancer » : un résumé seul, le rangement suffit."""

    summary: Prose = Field(min_length=1, max_length=600)


class ReplanDrops(ReplanSummary):
    """« Réduire le périmètre » : des retraits seulement."""

    drop: list[Annotated[str, Field(pattern=TASK_REF)]] = Field(default_factory=list, max_length=50)


class ReplanAdds(ReplanSummary):
    """« Approfondir » : des ajouts seulement."""

    add: list[ReplanTaskDraft] = Field(default_factory=list, max_length=20)


class ReplanDraft(ReplanDrops, ReplanAdds):
    """Ce que le port reçoit : résumé, retraits et ajouts (vides hors des droits de l'option)."""


# --- Ce que le port rend ------------------------------------------------------------------------


@dataclass(frozen=True)
class WeekLoad:
    rank: int
    start_date: date
    before: int  # minutes prévues avant la proposition
    after: int  # minutes prévues après
    cap: int  # plafond de la semaine (85 %, ou `week_cap_override` pour la semaine en cours)


@dataclass(frozen=True)
class PreviewSaved:
    """La proposition rangée et enregistrée. `empty` : rien ne change. `kept` : retraits
    ignorés (le dernier quiz ou la dernière pratique d'une semaine, D105). `impossible` : le
    plafond ne tient pas une pratique et le quiz (F10) ; avec `finished`, parce que le
    programme est terminé (plus aucune semaine à replanifier).

    Cycle de vie de la version écrite (D106) : `impossible` → statut clos `impossible` ;
    `empty` sans option → statut clos `empty` ; ces deux-là ne sont jamais `pending` ni
    proposées à January. Sinon `pending` (attend la réponse de January dans la session), et les
    `pending` précédents du programme passent `superseded` (D99)."""

    version: int
    empty: bool
    added: int
    removed: int
    moved: int
    weeks_before: int
    weeks_after: int
    loads: list[WeekLoad]
    kept: int = 0
    impossible: bool = False
    finished: bool = False


@dataclass(frozen=True)
class Applied:
    version: int
    stale: bool  # les lignes ont changé depuis la proposition : rien n'est écrit


class ReplanStore(Protocol):
    async def context(
        self,
        user_id: str,
        program_id: str,
        *,
        trigger: ReplanTrigger,
        review_entry_id: str | None,
        available_minutes: int | None,
        message: str | None,
    ) -> ReplanContext:
        """Programme, bilan et options, budget, modules et tâches à faire par référence.
        `program_not_found` (404) si le programme n'est pas à l'utilisateur."""
        ...

    async def preview(
        self,
        user_id: str,
        session_id: str,
        program_id: str,
        draft: ReplanDraft,
        *,
        refs: Mapping[str, str],
        option: ReplanOption | None,
        revision: int,
        reason: str,
        week_cap_override: int | None,
    ) -> PreviewSaved:
        """Résout les références par `refs` (inconnues : ignorées), applique les droits de
        l'option, range et enregistre la version (statut : voir `PreviewSaved`) ; idempotent
        par `(session, revision)`. Jamais `planning_impossible` : `PreviewSaved.impossible`."""
        ...

    async def apply(self, user_id: str, session_id: str, program_id: str, version: int) -> Applied:
        """Applique la version (idempotent : déjà acceptée → `stale=False` sans écrire). Lignes
        changées depuis la proposition, ou version qui n'attend plus (`superseded` par une autre
        session, refusée, close) → `stale=True`, rien n'est écrit, jamais d'erreur. Le port
        prend lui-même le verrou du programme, avant sa transaction (F4)."""
        ...

    async def refuse(self, user_id: str, session_id: str, program_id: str, version: int) -> None:
        """La version est refusée, le plan actuel reste (idempotent)."""
        ...


def replan_unavailable() -> AppError:
    return AppError(
        "replan_unavailable", "La replanification n'est pas branchée sur ce moteur.", 503
    )


class _NoReplan:
    """Valeur par défaut du moteur (tests existants, démarrages sans la feature `replan`)."""

    async def context(
        self,
        user_id: str,
        program_id: str,
        *,
        trigger: ReplanTrigger,
        review_entry_id: str | None,
        available_minutes: int | None,
        message: str | None,
    ) -> ReplanContext:
        raise replan_unavailable()

    async def preview(
        self,
        user_id: str,
        session_id: str,
        program_id: str,
        draft: ReplanDraft,
        *,
        refs: Mapping[str, str],
        option: ReplanOption | None,
        revision: int,
        reason: str,
        week_cap_override: int | None,
    ) -> PreviewSaved:
        raise replan_unavailable()

    async def apply(self, user_id: str, session_id: str, program_id: str, version: int) -> Applied:
        raise replan_unavailable()

    async def refuse(self, user_id: str, session_id: str, program_id: str, version: int) -> None:
        raise replan_unavailable()


NO_REPLAN: ReplanStore = _NoReplan()
