"""Le débrief de l'entretien et son rangement (SPEC F10, 1, 18.3, D145).

`debrief` donne les échanges (dans `untrusted`) à l'Intervieweur : quatre notes, trois points
forts, trois corrections, la version améliorée de la réponse la plus faible et les points attendus
des questions ratées. Le code décide de ce qui se compte : la réponse la plus faible est celle de
la note interne la plus basse (la plus ancienne en cas d'égalité), les questions ratées celles
dont la note est de 2 au plus ; le modèle écrit, il ne choisit pas. La réponse améliorée est écrite
au nom de January : `text_claims` signale ce que son profil ne dit pas (`flags`), la réponse est
montrée « à vérifier ». Arrêté avant toute réponse : aucun appel, aucun débrief (`stopped`).

`save` range l'issue par le port, idempotent par session (SPEC 9.4) : le seul nœud qui écrit. Une
fiche de révision par question ratée : recto la question, verso les points d'une bonne réponse.
Le débrief ne fait jamais perdre les réponses : s'il échoue (réponse illisible après les nouveaux
essais, panne passagère, lenteur : `RECOVERABLE_CODES`, ou `DEBRIEF_CALL_TIMEOUT_S`), `save`
range quand même les échanges avec `debrief=None`, sans fiche, et le dit à January ; entretien
`debrief_failed` côté port (échanges non vides, pas de débrief), distinct de `stopped` (échanges
vides). Le plafond de tokens (`token_cap_reached`) et les autres erreurs arrêtent la session.
Journaux : identifiants et nombres seulement (17.2)."""

import asyncio
import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.nodes.interviewer.common import AGENT, RECOVERABLE_CODES, Node, context_of
from app.agents.nodes.interviewer.context import exchanges_block, head_vars, profile_block
from app.agents.nodes.interviewer.salary import without_unsourced_figures
from app.agents.prompts.loader import render_prompt
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.emit import emit
from app.agents.runtime.invoke import node_timeout
from app.agents.runtime.prose import shorten
from app.agents.runtime.structured import structured_call
from app.agents.state.interview import InterviewState
from app.agents.tools.interview_schema import (
    Debrief,
    Exchange,
    ExpectedPoints,
    InterviewContext,
    debrief_schema,
)
from app.agents.tools.study_schema import CardDraft
from app.agents.tools.text_claims import text_claims
from app.core.errors import AppError

DEBRIEF_REQUEST = "Write the interview debrief."
DEBRIEF_TIMEOUT_S = 300  # plafond du nœud (`node_timeout`)
DEBRIEF_CALL_TIMEOUT_S = 270.0  # plus court : le repli (rien à écrire) a de la marge
MISSED_MAX_NOTE = 2
FRONT_MAX = 300
NOTHING_TO_GRADE = "Interview ended. No answers to score."
DEBRIEF_FAILED = (
    "The debrief couldn't be written. Your answers are saved. No scores or review cards were made."
)

logger = logging.getLogger(__name__)


def weakest_index(exchanges: list[Exchange]) -> int:
    """La question de la note interne la plus basse (une réponse non notée passe après), la plus
    ancienne en cas d'égalité."""
    return min(exchanges, key=lambda e: (e.unrated, e.note, e.index)).index


def missed_indices(exchanges: list[Exchange]) -> list[int]:
    return [e.index for e in exchanges if e.note <= MISSED_MAX_NOTE]


def allowed_phrases(ctx: InterviewContext) -> list[str]:
    """Les expressions entières que la réponse peut écrire : l'entreprise et l'intitulé du poste,
    jamais un outil ni un chiffre de l'offre."""
    names = [ctx.role]
    if ctx.analysis is not None:
        names += [ctx.analysis.company or "", ctx.analysis.title]
    return list(dict.fromkeys(name for name in names if name))


def flagged_terms(text: str, ctx: InterviewContext) -> list[str]:
    """Les termes que le profil ne dit pas, sans doublon, dans l'ordre du texte."""
    claims = text_claims(text, ctx.profile, allowed=allowed_phrases(ctx))
    return list(dict.fromkeys(claim.term for claim in claims))


def revision_cards(exchanges: list[Exchange], debrief: Debrief) -> list[CardDraft]:
    """Une fiche par question ratée : recto la question, verso les points d'une bonne réponse."""
    points = {item.index: item.points for item in debrief.expected}
    by_index = {e.index: e for e in exchanges}
    return [
        CardDraft(
            front=shorten(by_index[index].question, FRONT_MAX),
            back="\n".join(f"- {point}" for point in points[index]),
        )
        for index in debrief.missed
        if index in by_index and index in points
    ]


def debrief_vars(
    ctx: InterviewContext, exchanges: list[Exchange], weakest: int, missed: list[int]
) -> dict[str, object]:
    return {
        **head_vars(ctx),
        "mode": "debrief",
        "answered": len(exchanges),
        "exchanges": exchanges_block(exchanges),
        "profile": profile_block(ctx),
        "weakest": weakest,
        "missed": ", ".join(str(index) for index in missed) or "aucune",
    }


def _once_each(items: list[ExpectedPoints], missed: list[int]) -> list[ExpectedPoints]:
    """Les points des seules questions ratées, une fois chacune (la première l'emporte)."""
    first: dict[int, ExpectedPoints] = {}
    for item in items:
        if item.index in missed:
            first.setdefault(item.index, item)
    return [first[index] for index in missed if index in first]


async def _written(deps: GraphDeps, ctx: InterviewContext, exchanges: list[Exchange]) -> Debrief:
    weakest, missed = weakest_index(exchanges), missed_indices(exchanges)
    prompt = render_prompt(AGENT, **debrief_vars(ctx, exchanges, weakest, missed))
    model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
    found = await structured_call(
        model,
        debrief_schema(missed),
        [SystemMessage(prompt), HumanMessage(DEBRIEF_REQUEST)],
        agent=AGENT,
        step="debrief",
        intent="Writing your debrief.",
    )
    update = {
        "weakest_index": weakest,
        "missed": missed,
        "expected": _once_each(found.expected, missed),
        "unrated": [e.index for e in exchanges if e.unrated],
    }
    return Debrief.model_validate(found.model_copy(update=update).model_dump())


async def _try_written(
    deps: GraphDeps, ctx: InterviewContext, exchanges: list[Exchange]
) -> Debrief | None:
    """Le débrief, ou `None` si le modèle n'a pas répondu à temps ou lisiblement : les réponses de
    January ne se perdent pas. Les autres erreurs (dont le plafond de tokens) remontent."""
    try:
        async with asyncio.timeout(DEBRIEF_CALL_TIMEOUT_S):
            return await _written(deps, ctx, exchanges)
    except (AppError, TimeoutError) as exc:
        code = exc.code if isinstance(exc, AppError) else "timeout"
        if code != "timeout" and code not in RECOVERABLE_CODES:
            raise
        logger.warning(
            "Intervieweur sans débrief (%s), réponses gardées : session %s, %d échange(s)",
            code,
            deps.session_id,
            len(exchanges),
        )
        return None


def make_debrief(deps: GraphDeps) -> Node:
    @node_timeout(DEBRIEF_TIMEOUT_S)
    async def debrief(state: InterviewState) -> InterviewState:
        """Le débrief des questions répondues ; aucune réponse : aucun appel, aucun débrief."""
        exchanges = [Exchange.model_validate(e) for e in state["exchanges"]]
        if not exchanges:
            return {"debrief": None, "flags": [], "cards": []}
        ctx = context_of(state)
        written = await _try_written(deps, ctx, exchanges)
        if written is None:  # les réponses sont rangées sans débrief (`save`)
            return {"debrief": None, "flags": [], "cards": []}
        if ctx.salary is not None:
            written = without_unsourced_figures(written, ctx.language)
        flags = flagged_terms(written.improved_answer, ctx)
        cards = [] if ctx.salary is not None else revision_cards(exchanges, written)
        logger.info(
            "Débrief écrit : session %s, %d question(s), %d ratée(s), %d terme(s) signalé(s)",
            deps.session_id,
            len(exchanges),
            len(written.missed),
            len(flags),
        )
        return {
            "debrief": written.model_dump(),
            "flags": flags,
            "cards": [card.model_dump() for card in cards],
        }

    return debrief


def _closing(debrief: Debrief | None, cards: list[CardDraft], answered: int) -> str:
    if debrief is None:  # sans réponse : arrêté ; avec des réponses : débrief en échec
        return DEBRIEF_FAILED if answered else NOTHING_TO_GRADE
    unscored = len(debrief.unrated)
    scored = answered - unscored
    questions = "question" if scored == 1 else "questions"
    text = f"Interview complete. {scored} {questions} scored. Your debrief is ready."
    if cards:
        noun = "card" if len(cards) == 1 else "cards"
        text += f" {len(cards)} review {noun} created."
    if unscored:
        answers = "answer" if unscored == 1 else "answers"
        text += f" {unscored} {answers} could not be scored."
    return text


def make_save(deps: GraphDeps) -> Node:
    @node_timeout()
    async def save(state: InterviewState) -> InterviewState:
        """L'issue de l'entretien, la seule écriture ; rejoué, le port relit celle de la session."""
        exchanges = [Exchange.model_validate(e) for e in state["exchanges"]]
        raw = state["debrief"]
        debrief = None if raw is None else Debrief.model_validate(raw)
        cards = [CardDraft.model_validate(c) for c in state["cards"]]
        await deps.ports.interviews.save_result(
            deps.user_id,
            deps.session_id,
            state["interview_id"],
            exchanges,
            debrief,
            state["flags"],
            cards,
        )
        logger.info(
            "Entretien rangé : session %s, entretien %s, %d échange(s), %d fiche(s)",
            deps.session_id,
            state["interview_id"],
            len(exchanges),
            len(cards),
        )
        text = _closing(debrief, cards, len(exchanges))
        emit("agent.message", {"message_id": f"{AGENT}-fin", "text": text}, agent=AGENT)
        return {"summary": text}

    return save
