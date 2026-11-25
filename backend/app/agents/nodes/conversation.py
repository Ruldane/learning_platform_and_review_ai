import re
from collections.abc import Sequence
from dataclasses import replace
from typing import Any, Protocol
from uuid import UUID

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from app.agents.nodes.concentration import training_outcome
from app.agents.nodes.feynman import FeynmanState
from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import message_text, node_timeout
from app.agents.runtime.played_model import refresh_updated_brief
from app.agents.runtime.speech import CitationEntry, extract_citations, speak
from app.agents.tools.conversation_port import (
    BRAIN_LIBRARIAN,
    CLASSMATE_ROLES,
    CLASSROOM_SCOPE,
    OFFERS_ADVISER,
    TRAINING_TUTOR,
    TURN_TOKEN_LIMIT,
    ClassmateReply,
    ConversationContext,
    ConversationExchange,
    ConversationPractice,
    ConversationReference,
    ConversationSource,
    FocusOutcome,
)
from app.core.errors import AppError
from app.providers.llm.limits import with_output_limit

MAX_HITS = 6
MAX_EXCERPT = 600
MAX_ANSWER = 5_000
MAX_INPUT_BYTES = 8_800
MAX_OUTPUT_TOKENS = 2_800
CLASSROOM_INPUT_BYTES = 2_650
CLASSROOM_OUTPUT_TOKENS = 450
CLASSROOM_MAX_WORDS = 115
TOKEN_OVERHEAD = 400
MIN_OUTPUT_TOKENS = 300
_REVISION = re.compile(
    r"^(?:À revoir|To review)\s+\[(\d{1,2})]\s*:\s*(.{1,500}?)\s*→\s*(.{1,1000})$",
    re.MULTILINE,
)


class ConversationState(FeynmanState, total=False):
    answer: str
    sources: list[dict[str, Any]]
    practice: list[dict[str, Any]]
    classmates: list[dict[str, Any]]
    context_notes: dict[str, str] | None
    focus_outcome: FocusOutcome | None


class Node(Protocol):
    async def __call__(self, state: ConversationState) -> ConversationState: ...


async def _memory_sources(deps: GraphDeps, question: str) -> list[ConversationReference]:
    try:
        memory = await deps.memory.search(
            deps.user_id,
            question,
            kinds=("skill", "document", "decision"),
            k=MAX_HITS,
        )
    except AppError as exc:
        if exc.status_code == 503:
            return []
        raise
    sources: dict[str, ConversationSource] = {}
    for hit in memory.hits:
        if hit.item_id not in sources:
            sources[hit.item_id] = ConversationSource(
                kind="memory", id=UUID(hit.item_id), title=hit.title, excerpt=hit.text[:MAX_EXCERPT]
            )
    return [ConversationReference(source, source.excerpt or "") for source in sources.values()]


def _fit(text: str, limit: int) -> str:
    return text.encode()[: max(0, limit)].decode(errors="ignore")


def _catalog_text(refs: Sequence[ConversationReference], limit: int) -> str:
    def render(bodies: list[str]) -> str:
        return "\n\n".join(
            f"[{index}] {untrusted(_fit(ref.source.title, 200) + '\n' + body, 'reference')}"
            for index, (ref, body) in enumerate(zip(refs, bodies, strict=True), 1)
        )

    bodies = ["" if r.primary else _fit(r.material, 160) for r in refs]
    local_count = sum(r.primary for r in refs)
    if not local_count:
        return render(bodies)
    room = max(0, limit - len(render(bodies).encode())) // local_count
    return render(
        [
            _fit(ref.material, room) if ref.primary else body
            for ref, body in zip(refs, bodies, strict=True)
        ]
    )


def _messages(
    context: ConversationContext,
    refs: Sequence[ConversationReference],
    *,
    classroom: bool = False,
) -> list[BaseMessage]:
    history = "\n".join(
        f"Question: {turn.question}\nAnswer: {turn.answer}" for turn in context.history
    )
    history = history.encode()[-(450 if classroom else 650) :].decode(errors="ignore")
    selection = untrusted(
        _fit(context.selection or "", 450 if classroom else 1200), "selected passage"
    )
    suffix = (
        f"\n\nPrevious exchanges:\n{untrusted(history, 'conversation')}\n\n"
        f"Selected passage:\n{selection}\n\n"
        f"Current question:\n{_fit(context.question, 850 if classroom else 2400)}"
    )
    system = render_prompt(context.agent, mode=context.mode)
    prefix = "References:\n"
    fixed = len((system + prefix + suffix).encode())
    input_limit = CLASSROOM_INPUT_BYTES if classroom else MAX_INPUT_BYTES
    catalog = _catalog_text(refs, input_limit - fixed)
    return [SystemMessage(system), HumanMessage(prefix + catalog + suffix)]


def _output_budget(
    deps: GraphDeps,
    context: ConversationContext,
    messages: list[BaseMessage],
    *,
    reserved: int | None = None,
    output_limit: int = MAX_OUTPUT_TOKENS,
) -> int:
    spent = context.used_tokens + sum(len(message_text(msg).encode()) for msg in messages)
    cap = (
        reserved if reserved is not None else min(TURN_TOKEN_LIMIT, deps.settings.session_token_cap)
    )
    available = cap - spent - TOKEN_OVERHEAD
    if available < MIN_OUTPUT_TOKENS:
        raise AppError(
            "conversation_budget_reached", "This turn reached its conversation budget.", 429
        )
    return min(output_limit, available)


def _practice_of(answer: str, sources: list[ConversationSource]) -> list[dict[str, Any]]:
    practice = []
    for match in _REVISION.finditer(answer):
        raw, front, back = match.groups()
        index = int(raw) - 1
        if 0 <= index < len(sources) and sources[index].kind == "lesson":
            card = ConversationPractice(
                lesson_id=sources[index].id, front=front.strip(), back=back.strip()
            )
            if card.front and card.back:
                practice.append(card.model_dump(mode="json"))
        if len(practice) == 3:
            break
    return practice


async def _classroom_reply(deps: GraphDeps, context: ConversationContext) -> ConversationState:
    """Three fixed roles share a turn's reserve and the same published lesson."""
    reserve = min(TURN_TOKEN_LIMIT, deps.settings.session_token_cap) - context.used_tokens
    reserve_per_role = reserve // len(CLASSMATE_ROLES)
    refs = context.references
    catalog = [CitationEntry(i, ref.source.title) for i, ref in enumerate(refs, 1)]
    model = await deps.models.get_chat_model(
        deps.user_id, "strong" if context.strong else "fast", agent=TRAINING_TUTOR
    )
    history = list(context.history)
    replies = []
    for role in CLASSMATE_ROLES:
        mode = f"classroom_{role}"
        current = replace(context, mode=mode, history=history, used_tokens=0)
        messages = _messages(current, refs, classroom=True)
        output = _output_budget(
            deps, current, messages, reserved=reserve_per_role, output_limit=CLASSROOM_OUTPUT_TOKENS
        )
        spoken = await speak(
            with_output_limit(refresh_updated_brief(model), output),
            messages,
            agent=TRAINING_TUTOR,
            step=mode,
            intent="I am responding to your explanation as a classmate.",
            catalog=catalog,
            max_words=CLASSROOM_MAX_WORDS,
            retry=False,
        )
        answer = spoken.text[:1400]
        if not answer:
            raise AppError("classroom_reply_empty", "A classmate did not reply. Try again.", 503)
        replies.append(ClassmateReply(role=role, answer=answer))
        history.append(ConversationExchange("Reply in this turn", f"{role}: {answer[:140]}"))
    return {
        "answer": "\n\n".join(reply.answer for reply in replies),
        "classmates": [reply.model_dump(mode="json") for reply in replies],
        "sources": [ref.source.model_dump(mode="json") for ref in refs],
    }


def _reply_fields(
    text: str,
    context: ConversationContext,
    sources: list[ConversationSource],
    catalog: list[CitationEntry],
) -> ConversationState:
    training = context.agent == TRAINING_TUTOR
    raw, outcome = training_outcome(text) if training else (text, None)
    answer = raw[:MAX_ANSWER]
    return {
        "answer": answer,
        "sources": [
            sources[c.index - 1].model_dump(mode="json") for c in extract_citations(answer, catalog)
        ],
        "practice": _practice_of(answer, sources) if training else [],
        "context_notes": context.context_notes,
        "focus_outcome": outcome,
    }


def make_reply(deps: GraphDeps) -> Node:
    @node_timeout()
    async def reply(state: ConversationState) -> ConversationState:
        context = await deps.ports.conversations.context(
            deps.user_id, deps.session_id, state["thread_id"], state["turn_id"]
        )
        if context is None:
            return {}
        if context.mode == CLASSROOM_SCOPE:
            return await _classroom_reply(deps, context)
        refs = list(context.references)
        if context.agent not in (BRAIN_LIBRARIAN, OFFERS_ADVISER):
            refs.extend(await _memory_sources(deps, context.question))
        sources = [reference.source for reference in refs]
        messages = _messages(context, refs)
        max_output = _output_budget(deps, context, messages)
        model = await deps.models.get_chat_model(
            deps.user_id, "strong" if context.strong else "fast", agent=context.agent
        )
        catalog = [
            CitationEntry(
                index,
                source.title,
                memory_item_id=str(source.id) if source.kind == "memory" else None,
            )
            for index, source in enumerate(sources, 1)
        ]
        spoken = await speak(
            with_output_limit(refresh_updated_brief(model), max_output),
            messages,
            agent=context.agent,
            step="reponse",
            intent=(
                "I help you make sense of your saved job offers."
                if context.agent == OFFERS_ADVISER
                else "I help you study."
            ),
            catalog=catalog,
            max_words=600,
            retry=False,
        )
        return _reply_fields(spoken.text, context, sources, catalog)

    return reply


def make_save(deps: GraphDeps) -> Node:
    async def save(state: ConversationState) -> ConversationState:
        if "answer" in state:
            await deps.ports.conversations.save_reply(
                deps.user_id,
                deps.session_id,
                state["thread_id"],
                state["turn_id"],
                answer=state["answer"],
                sources=[ConversationSource.model_validate(source) for source in state["sources"]],
                practice=[
                    ConversationPractice.model_validate(card) for card in state.get("practice", [])
                ],
                context_notes=state.get("context_notes"),
                focus_outcome=state.get("focus_outcome"),
                classmates=[
                    ClassmateReply.model_validate(reply) for reply in state.get("classmates", [])
                ],
            )
        return {"summary": "Reply saved."}

    return save
