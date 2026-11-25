"""The Moderator of the daily brief (P11, D161): the Council's two sentences of advice, in the
Council's name.

The code counts the day's facts (block, reviews, follow-ups, postings, progress: feature `brief`),
renders them as sentences (`facts_text`, wrapped by `untrusted`) and **checks every number of
the advice**: a number the facts do not state (an invented "3 hours") makes it ask again once,
naming it, then the advice is stored as `None` (section `failed`): never a wrong figure. The
allowed numbers are the port's `allowed_numbers`, plus those of the block title that the code
shows.

A model failure, an invalid format or a timeout also empty the advice without stopping the flow
(the resource is a separate section).

Logs: identifiers, numbers and codes only, never a fact, a title or a sentence
(17.2)."""

import asyncio
import logging
from collections.abc import Callable

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.errors import GraphInterrupt

from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.structured import structured_call
from app.agents.state.daily_brief import DailyBriefState, Node
from app.agents.tools.brief_port import MODEL_UNAVAILABLE_CODES, AdviceFacts, BriefContext
from app.agents.tools.brief_schema import CouncilAdvice, numbers_in_advice
from app.core.errors import AppError

AGENT = "moderator"
ASKS = 2  # one request, then a single re-request that names the invented number
BUDGET_S = 90.0  # shorter than the node cap: a timeout empties the advice, not the brief
LANGUAGES = {"fr": "French", "en": "English"}

logger = logging.getLogger(__name__)


def _plural(number: int, one: str, many: str) -> str:
    return f"{number} {one if number < 2 else many}"


def _line(number: int | None, make: Callable[[int], str]) -> list[str]:
    """The line of a fact, or nothing if its section was down (never an invented zero)."""
    return [] if number is None else [make(number)]


def _facts_fr(facts: AdviceFacts) -> list[str]:
    # French variant: kept on purpose, for users whose language setting is `fr`.
    if facts.block_minutes is None:
        block: list[str] = []
    elif facts.block_title:
        title = " ".join(facts.block_title.split())
        block = [
            f"Bloc d'étude du jour : « {title} », "
            f"{_plural(facts.block_minutes, 'minute', 'minutes')}."
        ]
    else:
        block = ["Aucun bloc d'étude prévu aujourd'hui."]
    score = (
        [f"Meilleur score de quiz récent : {facts.best_score}."]
        if facts.best_score is not None
        else []
    )
    week = (
        []
        if facts.week_done is None or facts.week_planned is None
        else [
            f"Cette semaine : {_plural(facts.week_done, 'tâche faite', 'tâches faites')}, "
            f"{_plural(facts.week_planned, 'prévue', 'prévues')}."
        ]
    )
    return [
        *block,
        *_line(facts.cards_due, lambda n: f"À réviser : {_plural(n, 'fiche', 'fiches')}."),
        *_line(
            facts.reminders_due,
            lambda n: f"À relancer : {_plural(n, 'candidature', 'candidatures')}.",
        ),
        *_line(facts.offers, lambda n: f"À regarder : {_plural(n, 'offre', 'offres')}."),
        *score,
        *week,
        *_line(
            facts.streak_days,
            lambda n: f"Série en cours : {_plural(n, 'jour', 'jours')} de suite.",
        ),
    ]


def _facts_en(facts: AdviceFacts) -> list[str]:
    if facts.block_minutes is None:
        block: list[str] = []
    elif facts.block_title:
        title = " ".join(facts.block_title.split())
        block = [
            f'Study block of the day: "{title}", '
            f"{_plural(facts.block_minutes, 'minute', 'minutes')}."
        ]
    else:
        block = ["No study block planned today."]
    score = [f"Best recent quiz score: {facts.best_score}."] if facts.best_score is not None else []
    week = (
        []
        if facts.week_done is None or facts.week_planned is None
        else [
            f"This week: {_plural(facts.week_done, 'task', 'tasks')} done out of "
            f"{facts.week_planned} planned."
        ]
    )
    return [
        *block,
        *_line(facts.cards_due, lambda n: f"To review: {_plural(n, 'card', 'cards')}."),
        *_line(
            facts.reminders_due,
            lambda n: f"To follow up: {_plural(n, 'application', 'applications')}.",
        ),
        *_line(facts.offers, lambda n: f"To look at: {_plural(n, 'posting', 'postings')}."),
        *score,
        *week,
        *_line(
            facts.streak_days,
            lambda n: f"Current streak: {_plural(n, 'day', 'days')} in a row.",
        ),
    ]


def facts_text(ctx: BriefContext) -> str:
    """The day's facts as sentences, written by the code (the model receives no other figure),
    wrapped as data."""
    lines = _facts_fr(ctx.facts) if ctx.language == "fr" else _facts_en(ctx.facts)
    return untrusted("\n".join(lines), "facts of the day")


def invented_numbers(sentences: list[str], ctx: BriefContext) -> list[str]:
    """The advice numbers that neither `allowed_numbers` nor the block title allow, sorted."""
    allowed = set(ctx.allowed_numbers)
    if ctx.facts.block_title:
        allowed |= numbers_in_advice([ctx.facts.block_title])
    return sorted(numbers_in_advice(sentences) - allowed)


def _correction(numbers: list[str]) -> str:
    return (
        f"Your advice cites {', '.join(numbers)}, which is not among the facts of the day. "
        "Rewrite it with no number other than those of the facts of the day."
    )


async def advise(deps: GraphDeps, ctx: BriefContext) -> list[str] | None:
    """The advice's two sentences, or `None` if the model cites an invented number twice."""
    prompt = render_prompt(
        AGENT, mode="brief", facts=facts_text(ctx), language=LANGUAGES[ctx.language]
    )
    model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
    messages: list[BaseMessage] = [SystemMessage(prompt), HumanMessage("Write today's advice.")]
    for ask in range(ASKS):
        advice = await structured_call(
            model,
            CouncilAdvice,
            messages,
            agent=AGENT,
            step=f"conseil-{ask + 1}",
            intent="writing today's advice",
        )
        wrong = invented_numbers(advice.sentences, ctx)
        if not wrong:
            return advice.sentences
        logger.info(
            "Advice refused: session %s, attempt %d, %d invented number(s)",
            deps.session_id,
            ask + 1,
            len(wrong),
        )
        messages += [AIMessage(advice.model_dump_json()), HumanMessage(_correction(wrong))]
    return None


def make_advice(deps: GraphDeps) -> Node:
    @node_timeout()
    async def advice(state: DailyBriefState) -> DailyBriefState:
        """The "advice" section: skipped if already stored (node replayed). Impossible advice is
        stored as `None` (section `failed`) and the flow ends anyway."""
        brief_id = state["brief_id"]
        ctx = await deps.ports.brief.context(deps.user_id, brief_id)
        if ctx.advice_done:
            return {}
        sentences: list[str] | None = None
        unavailable = False
        try:
            async with asyncio.timeout(BUDGET_S):
                sentences = await advise(deps, ctx)
        except GraphInterrupt:
            raise
        except Exception as exc:  # a section that is down does not stop the other
            code = exc.code if isinstance(exc, AppError) else type(exc).__name__
            unavailable = code in MODEL_UNAVAILABLE_CODES  # no model: "unavailable"
            logger.info("Brief advice impossible: session %s, cause %s", deps.session_id, code)
        await deps.ports.brief.save_advice(
            deps.user_id, deps.session_id, brief_id, sentences, unavailable=unavailable
        )
        logger.info(
            "Brief advice stored: session %s, brief %s, written %s",
            deps.session_id,
            brief_id,
            sentences is not None,
        )
        return {}

    return advice
