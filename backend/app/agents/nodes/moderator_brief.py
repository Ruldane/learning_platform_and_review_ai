"""Le Modérateur du brief du jour (P11, D161) : les deux phrases du conseil, au nom du Conseil.

Le code compte les faits du jour (bloc, révisions, relances, offres, avancement : feature `brief`),
les rend en phrases (`facts_text`, encadrées par `untrusted`) et **contrôle chaque nombre du
conseil** : un nombre que les faits ne disent pas (« 3 heures » inventé) fait redemander une fois,
en le nommant, puis le conseil est rangé `None` (rubrique `failed`) : jamais un chiffre faux. Les
nombres permis sont `allowed_numbers` du port, plus ceux du titre du bloc que le code montre.

Une panne du modèle, un format invalide ou un dépassement de délai vident aussi le conseil sans
arrêter le parcours (la ressource est une rubrique à part).

Journaux : identifiants, nombres et codes seulement, jamais un fait, un titre ni une phrase
(17.2)."""

import asyncio
import logging

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.structured import structured_call
from app.agents.state.daily_brief import DailyBriefState, Node
from app.agents.tools.brief_port import AdviceFacts, BriefContext
from app.agents.tools.brief_schema import CouncilAdvice, numbers_in_advice
from app.core.errors import AppError

AGENT = "moderator"
ASKS = 2  # une demande, puis une seule re-demande qui nomme le nombre inventé
BUDGET_S = 90.0  # plus court que le plafond du nœud : un dépassement vide le conseil, pas le brief
LANGUAGES = {"fr": "français", "en": "anglais"}

logger = logging.getLogger(__name__)


def _plural(number: int, one: str, many: str) -> str:
    return f"{number} {one if number < 2 else many}"


def _facts_fr(facts: AdviceFacts) -> list[str]:
    block = (
        f"Bloc d'étude du jour : « {' '.join(facts.block_title.split())} », "
        f"{_plural(facts.block_minutes, 'minute', 'minutes')}."
        if facts.block_title
        else "Aucun bloc d'étude prévu aujourd'hui."
    )
    score = (
        [f"Meilleur score de quiz récent : {facts.best_score}."]
        if facts.best_score is not None
        else []
    )
    return [
        block,
        f"À réviser : {_plural(facts.cards_due, 'fiche', 'fiches')}.",
        f"À relancer : {_plural(facts.reminders_due, 'candidature', 'candidatures')}.",
        f"À regarder : {_plural(facts.offers, 'offre', 'offres')}.",
        *score,
        f"Cette semaine : {_plural(facts.week_done, 'bloc fait', 'blocs faits')}, "
        f"{_plural(facts.week_planned, 'prévu', 'prévus')}.",
        f"Série en cours : {_plural(facts.streak_days, 'jour', 'jours')} de suite.",
    ]


def _facts_en(facts: AdviceFacts) -> list[str]:
    block = (
        f'Study block of the day: "{" ".join(facts.block_title.split())}", '
        f"{_plural(facts.block_minutes, 'minute', 'minutes')}."
        if facts.block_title
        else "No study block planned today."
    )
    score = [f"Best recent quiz score: {facts.best_score}."] if facts.best_score is not None else []
    return [
        block,
        f"To review: {_plural(facts.cards_due, 'card', 'cards')}.",
        f"To follow up: {_plural(facts.reminders_due, 'application', 'applications')}.",
        f"To look at: {_plural(facts.offers, 'posting', 'postings')}.",
        *score,
        f"This week: {facts.week_done} done out of {facts.week_planned} planned.",
        f"Current streak: {_plural(facts.streak_days, 'day', 'days')} in a row.",
    ]


def facts_text(ctx: BriefContext) -> str:
    """Les faits du jour en phrases, écrites par le code (le modèle ne reçoit aucun autre chiffre),
    encadrées comme données."""
    lines = _facts_fr(ctx.facts) if ctx.language == "fr" else _facts_en(ctx.facts)
    return untrusted("\n".join(lines), "faits du jour")


def invented_numbers(sentences: list[str], ctx: BriefContext) -> list[str]:
    """Les nombres du conseil que ni `allowed_numbers` ni le titre du bloc ne permettent, triés."""
    allowed = set(ctx.allowed_numbers)
    if ctx.facts.block_title:
        allowed |= numbers_in_advice([ctx.facts.block_title])
    return sorted(numbers_in_advice(sentences) - allowed)


def _correction(numbers: list[str]) -> str:
    return (
        f"Ton conseil cite {', '.join(numbers)}, qui ne figure pas parmi les faits du jour. "
        "Réécris-le sans aucun autre nombre que ceux des faits du jour."
    )


async def advise(deps: GraphDeps, ctx: BriefContext) -> list[str] | None:
    """Les deux phrases du conseil, ou `None` si le modèle cite deux fois un nombre inventé."""
    prompt = render_prompt(
        AGENT, mode="brief", facts=facts_text(ctx), language=LANGUAGES[ctx.language]
    )
    model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
    messages: list[BaseMessage] = [SystemMessage(prompt), HumanMessage("Écris le conseil du jour.")]
    for ask in range(ASKS):
        advice = await structured_call(
            model,
            CouncilAdvice,
            messages,
            agent=AGENT,
            step=f"conseil-{ask + 1}",
            intent="j'écris le conseil du jour",
        )
        wrong = invented_numbers(advice.sentences, ctx)
        if not wrong:
            return advice.sentences
        logger.info(
            "Conseil refusé : session %s, essai %d, %d nombre(s) inventé(s)",
            deps.session_id,
            ask + 1,
            len(wrong),
        )
        messages += [AIMessage(advice.model_dump_json()), HumanMessage(_correction(wrong))]
    return None


def make_advice(deps: GraphDeps) -> Node:
    @node_timeout()
    async def advice(state: DailyBriefState) -> DailyBriefState:
        """La rubrique « conseil » : sautée si elle est déjà rangée (nœud rejoué). Un conseil
        impossible est rangé `None` (rubrique `failed`) et le parcours se termine quand même."""
        brief_id = state["brief_id"]
        ctx = await deps.ports.brief.context(deps.user_id, brief_id)
        if ctx.advice_done:
            return {}
        sentences: list[str] | None = None
        try:
            async with asyncio.timeout(BUDGET_S):
                sentences = await advise(deps, ctx)
        except Exception as exc:  # une rubrique en panne n'arrête pas l'autre
            code = exc.code if isinstance(exc, AppError) else type(exc).__name__
            logger.info("Conseil du brief impossible : session %s, cause %s", deps.session_id, code)
        await deps.ports.brief.save_advice(deps.user_id, deps.session_id, brief_id, sentences)
        logger.info(
            "Conseil du brief rangé : session %s, brief %s, écrit %s",
            deps.session_id,
            brief_id,
            sentences is not None,
        )
        return {}

    return advice
