"""Les deux messages d'un appel du professeur (10.A3). Le **début fixe** (`prefix_of`) ne dépend que
de l'exercice et du style : il est identique, octet pour octet, d'un appel à l'autre d'une séance,
et marqué pour la mise en cache. Tout ce qui change (déclencheur, niveau, code, erreur, échanges)
est dans le message suivant (`turn_of`)."""

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.nodes.professor.context import TeacherContext
from app.agents.nodes.professor.plan import Plan, Trigger
from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.tools.ide_port import TeachInputs
from app.providers.llm.base import CACHE_PREFIX_KEY

AGENT = "professor"
FREE_STATEMENT = "(séance libre : pas d'énoncé)"
TRIGGERS = {
    "run_error": "son code vient d'échouer",
    "question": "elle pose une question",
    "hint": "elle demande un indice",
    "idle": "elle est arrêtée sur cette ligne depuis un moment",
}


def prefix_of(inputs: TeachInputs) -> SystemMessage:
    """Consignes et énoncé : stable pour un même exercice et un même style."""
    statement = f"{inputs.title}\n\n{inputs.statement or FREE_STATEMENT}"
    text = render_prompt(
        AGENT, mode="prefix", style=inputs.style, exercise=untrusted(statement, "énoncé")
    )
    return SystemMessage(text, additional_kwargs={CACHE_PREFIX_KEY: True})


def _task(plan: Plan) -> str:
    if len(plan.kinds) > 1:
        return "either"
    return "explanation" if plan.kind == "explanation" else plan.kind


def turn_of(
    inputs: TeachInputs,
    plan: Plan,
    ctx: TeacherContext,
    *,
    trigger: Trigger,
    level: int,
    question: str | None,
) -> HumanMessage:
    """La demande de cet appel : tâche, déclencheur, question, fichier, erreur, échanges."""
    where = f"{ctx.path}, lignes {ctx.first_line} à {ctx.last_line} sur {ctx.line_count}"
    exchanges = "\n".join(f"- {line}" for line in ctx.exchanges)
    text = render_prompt(
        AGENT,
        mode="turn",
        task=_task(plan),
        level=level,
        trigger=TRIGGERS[trigger],
        question=untrusted(question, "question de January") if question else "",
        code=untrusted(f"Ligne en cause : {ctx.focus}\n{ctx.window}", f"code ({where})"),
        error=untrusted(ctx.error_tail, "fin de la sortie") if ctx.error_tail else "",
        exchanges=untrusted(exchanges, "derniers échanges") if exchanges else "",
    )
    return HumanMessage(text)
