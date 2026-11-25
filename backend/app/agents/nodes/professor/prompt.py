"""The two messages of a professor call (10.A3). The **fixed start** (`prefix_of`) only depends
on the exercise and the style: it is identical, byte for byte, from one call to the next of a
session, and marked for caching. Everything that changes (trigger, level, code, error,
exchanges) is in the next message (`turn_of`)."""

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.nodes.professor.context import TeacherContext
from app.agents.nodes.professor.plan import Plan, Trigger
from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.tools.ide_port import TeachInputs
from app.providers.llm.base import CACHE_PREFIX_KEY

AGENT = "professor"
FREE_STATEMENT = "(free session with no exercise statement)"
TRIGGERS = {
    "run_error": "her code just failed",
    "question": "she is asking a question",
    "hint": "she is asking for a hint",
    "idle": "she has been stuck on this line for a while",
}


def prefix_of(inputs: TeachInputs) -> SystemMessage:
    """Instructions and statement: stable for the same exercise and the same style."""
    statement = f"{inputs.title}\n\n{inputs.statement or FREE_STATEMENT}"
    text = render_prompt(
        AGENT, mode="prefix", style=inputs.style, exercise=untrusted(statement, "statement")
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
    """The request of this call: task, trigger, question, file, error, exchanges."""
    where = f"{ctx.path}, lines {ctx.first_line} to {ctx.last_line} of {ctx.line_count}"
    exchanges = "\n".join(f"- {line}" for line in ctx.exchanges)
    files = "\n".join(f"- {path}" for path in ctx.project_paths)
    projection = f"Line at issue: {ctx.focus}\n{ctx.window}\n\nProject files:\n{files}"
    text = render_prompt(
        AGENT,
        mode="turn",
        task=_task(plan),
        level=level,
        trigger=TRIGGERS[trigger],
        question=untrusted(question, "January's question") if question else "",
        code=untrusted(projection, f"code ({where})"),
        error=untrusted(ctx.error_tail, "end of the output") if ctx.error_tail else "",
        exchanges=untrusted(exchanges, "conversation thread, oldest to most recent")
        if exchanges
        else "",
    )
    return HumanMessage(text)
