"""Pick the professor's note type and model tier before the call (10.A3).

Use fast for hints and annotations and strong for explanations and proposed fixes.
"""

from dataclasses import dataclass
from typing import Literal

from app.agents.tools.ide_schema import TeacherKind
from app.providers.llm.base import Tier

Trigger = Literal["run_error", "run_ok", "question", "hint", "idle"]
MAX_LEVEL = 3


@dataclass(frozen=True)
class Plan:
    kinds: tuple[TeacherKind, ...]  # Allowed kinds in order, with the default first.
    tier: Tier

    @property
    def kind(self) -> TeacherKind:
        return self.kinds[0]


def plan_of(trigger: Trigger, style: Literal["guide", "pair"]) -> Plan:
    """Use hints in guide mode and annotations in pair mode for errors or inactivity.

    Explicit hints are incremental. Questions allow explanations and, in pair mode, proposed
    fixes. A successful run needs no model.
    """
    if trigger == "run_ok":
        raise ValueError("run_ok does not call the model")
    if trigger == "question":
        return Plan(("explanation",) if style == "guide" else ("explanation", "proposal"), "strong")
    if trigger == "hint" or style == "guide":
        return Plan(("hint",), "fast")
    return Plan(("annotation",), "fast")
