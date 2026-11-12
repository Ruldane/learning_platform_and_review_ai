"""Variables du prompt `plan` du Stratège (D86), tirées du contexte du port `ProgramStore`.

Les propositions et le compte rendu sont des sorties d'agents, le plan courant mêle des textes de
January et du Stratège : tous sont encadrés par `untrusted()` (17.4). L'objectif et le cadrage
sont les souhaits de January : non encadrés (D53 §5, D84), jamais journalisés."""

from typing import Any

from app.agents.prompts.loader import untrusted
from app.agents.tools.council_port import ProposalDraft
from app.agents.tools.plan_schema import KnownSkills
from app.agents.tools.program_port import ProgramContext

_LEVELS = {
    "declare": "déclaré",
    "en_cours": "en cours",
    "valide": "validé",
    "prouve": "prouvé",
}
_LANGUAGES = {"fr": "français", "en": "anglais"}


def hours(minutes: int) -> str:
    """`750` → « 12 h 30 », `600` → « 10 h »."""
    whole, rest = divmod(minutes, 60)
    return f"{whole} h {rest:02d}" if rest else f"{whole} h"


def _known(known: KnownSkills) -> str:
    if not known:
        return "Aucun acquis connu."
    lines = [f"- {name} ({_LEVELS.get(level, level)})" for name, level in sorted(known.items())]
    return "\n".join(lines)


def _proposal(rank: int, proposal: ProposalDraft) -> str:
    text = "\n".join(
        [
            f"Nom : {proposal.name}",
            f"Promesse : {proposal.promise}",
            f"Durée : {proposal.duration_weeks} semaines, {proposal.weekly_hours} h par semaine",
            f"Compétences : {', '.join(proposal.skills)}",
            f"Projet final : {proposal.final_project}",
            f"Compromis : {' ; '.join(proposal.tradeoffs)}",
        ]
    )
    return untrusted(text, f"proposition {rank}")


def context_vars(ctx: ProgramContext) -> dict[str, Any]:
    """Variables JSON du prompt (gardées dans l'état du graphe)."""
    goal, budget = ctx.goal, ctx.budget
    framing = [f"- {answer}" for answer in goal.framing.values() if answer.strip()]
    minutes = ctx.council_minutes
    return {
        "goal": goal.text,
        "target_role": goal.target_role or "non précisé",
        "deadline": goal.deadline.strftime("%d/%m/%Y") if goal.deadline else "aucune",
        "framing": "\n".join(framing) or "Aucune réponse de cadrage.",
        "weekly_minutes": budget.weekly_minutes,
        "cap_minutes": budget.cap_minutes,
        "cap_hours": hours(budget.cap_minutes),
        "weekday_minutes": budget.weekday_minutes,
        "weekend_minutes": budget.weekend_minutes,
        "known": _known(ctx.known_skills),
        "mix": len(ctx.proposals) > 1,
        "proposals": "\n\n".join(_proposal(n, p) for n, p in enumerate(ctx.proposals, start=1)),
        "minutes": untrusted(minutes, "compte rendu du Scribe") if minutes else "",
        "current_plan": untrusted(ctx.current_plan, "plan courant") if ctx.current_plan else "",
        "language": _LANGUAGES.get(ctx.language, ctx.language),
    }
