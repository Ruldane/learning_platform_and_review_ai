"""Ce que le professeur fait pour un déclencheur et un style (10.A3) : le type de note permis et le
niveau de modèle. Choisis par le code **avant** l'appel (le modèle ne choisit jamais son prix) :
le niveau léger (`rapide`) pour les indices et les annotations en marge, le niveau fort pour les
vraies explications et les corrections proposées."""

from dataclasses import dataclass
from typing import Literal

from app.agents.tools.ide_schema import TeacherKind
from app.providers.llm.base import Tier

Trigger = Literal["run_error", "run_ok", "question", "hint", "idle"]
MAX_LEVEL = 3


@dataclass(frozen=True)
class Plan:
    kinds: tuple[TeacherKind, ...]  # types de note permis ; le premier est celui par défaut
    tier: Tier

    @property
    def kind(self) -> TeacherKind:
        return self.kinds[0]


def plan_of(trigger: Trigger, style: Literal["guide", "pair"]) -> Plan:
    """`hint` : un indice gradué (léger). `run_error` et `idle` : un indice en mode guide, une
    annotation de marge en binôme (léger). `question` : une explication (fort) ; en binôme, une
    proposition de correction est aussi permise. `run_ok` n'appelle jamais le modèle."""
    if trigger == "run_ok":
        raise ValueError("run_ok n'appelle jamais le modèle")
    if trigger == "question":
        return Plan(("explanation",) if style == "guide" else ("explanation", "proposal"), "fort")
    if trigger == "hint" or style == "guide":
        return Plan(("hint",), "rapide")
    return Plan(("annotation",), "rapide")
