"""Variables of the Strategist's `plan` prompt (D86), taken from the `ProgramStore` port context.

The proposals and the minutes are agent outputs, the current plan mixes January's and the
Strategist's texts, the acquired skills partly come from memory: all are wrapped by
`untrusted()` (17.4). The goal and the framing are January's wishes: not wrapped (D53 section 5,
D84), never logged."""

from typing import Any

from app.agents.prompts.loader import untrusted
from app.agents.tools.council_port import ProposalDraft
from app.agents.tools.plan_schema import KnownSkills
from app.agents.tools.program_port import ProgramContext

_LEVELS = {
    "declared": "declared",
    "in_progress": "in progress",
    "validated": "validated",
    "proven": "proven",
}
_LANGUAGES = {"fr": "French", "en": "English"}


def hours(minutes: int) -> str:
    """`750` -> "12 h 30", `600` -> "10 h"."""
    whole, rest = divmod(minutes, 60)
    return f"{whole} h {rest:02d}" if rest else f"{whole} h"


def _known(known: KnownSkills) -> str:
    """Wrapped by `untrusted()`: the names partly come from the memory's acquired skills (written
    by the Archivist from an imported document; reread of 4.5, D88)."""
    if not known:
        return "No known skills recorded."
    lines = [f"- {name} ({_LEVELS.get(level, level)})" for name, level in sorted(known.items())]
    return untrusted("\n".join(lines), "January's known skills")


def _proposal(rank: int, proposal: ProposalDraft) -> str:
    text = "\n".join(
        [
            f"Name: {proposal.name}",
            f"Promise: {proposal.promise}",
            f"Duration: {proposal.duration_weeks} weeks, {proposal.weekly_hours} h per week",
            f"Skills: {', '.join(proposal.skills)}",
            f"Final project: {proposal.final_project}",
            f"Trade-offs: {', '.join(proposal.tradeoffs)}",
        ]
    )
    return untrusted(text, f"proposal {rank}")


def context_vars(ctx: ProgramContext) -> dict[str, Any]:
    """JSON variables of the prompt (kept in the graph state)."""
    goal, budget = ctx.goal, ctx.budget
    framing = [f"- {answer}" for answer in goal.framing.values() if answer.strip()]
    minutes = ctx.council_minutes
    return {
        "goal": goal.text,
        "target_role": goal.target_role or "unspecified",
        "deadline": goal.deadline.strftime("%d/%m/%Y") if goal.deadline else "none",
        "framing": "\n".join(framing) or "No framing answers.",
        "weekly_minutes": budget.weekly_minutes,
        "cap_minutes": budget.cap_minutes,
        "cap_hours": hours(budget.cap_minutes),
        "floor_minutes": budget.floor_minutes,
        "weekday_minutes": budget.weekday_minutes,
        "weekend_minutes": budget.weekend_minutes,
        "known": _known(ctx.known_skills),
        "mix": len(ctx.proposals) > 1,
        "proposals": "\n\n".join(_proposal(n, p) for n, p in enumerate(ctx.proposals, start=1)),
        "minutes": untrusted(minutes, "Scribe's minutes") if minutes else "",
        "current_plan": untrusted(ctx.current_plan, "current plan") if ctx.current_plan else "",
        "language": _LANGUAGES.get(ctx.language, ctx.language),
    }
