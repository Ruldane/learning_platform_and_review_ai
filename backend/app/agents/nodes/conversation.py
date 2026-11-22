from collections.abc import Sequence
from typing import Any, Protocol, TypedDict
from uuid import UUID

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import message_text, node_timeout
from app.agents.runtime.played_model import refresh_updated_brief
from app.agents.runtime.speech import CitationEntry, extract_citations, speak
from app.agents.tools.conversation_port import (
    LESSON_PROFESSOR,
    TURN_TOKEN_LIMIT,
    ConversationContext,
    ConversationSource,
)
from app.core.errors import AppError
from app.providers.llm.limits import with_output_limit

MAX_HITS = 6
MAX_EXCERPT = 600
MAX_ANSWER = 5_000
MAX_INPUT_BYTES = 8_800
MAX_OUTPUT_TOKENS = 2_800
TOKEN_OVERHEAD = 400
MIN_OUTPUT_TOKENS = 300


class ConversationState(TypedDict, total=False):
    thread_id: str
    turn_id: str
    answer: str
    sources: list[dict[str, Any]]
    summary: str


class Node(Protocol):
    async def __call__(self, state: ConversationState) -> ConversationState: ...


async def _memory_sources(deps: GraphDeps, question: str) -> list[ConversationSource]:
    try:
        memory = await deps.memory.search(
            deps.user_id,
            question,
            kinds=("acquis", "document", "decision"),
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
    return list(sources.values())


def _fit(text: str, limit: int) -> str:
    return text.encode()[: max(0, limit)].decode(errors="ignore")


def _messages(
    context: ConversationContext, memory: Sequence[ConversationSource]
) -> list[BaseMessage]:
    history = "\n".join(
        f"Question : {turn.question}\nRéponse : {turn.answer}" for turn in context.history
    )
    history = history.encode()[-650:].decode(errors="ignore")
    other_sources = "\n\n".join(
        f"[{index}] {untrusted(_fit(f'{source.title}\n{source.excerpt or ""}', 220), 'référence')}"
        for index, source in enumerate(memory, 2)
    )
    selection = untrusted(_fit(context.source.excerpt or "", 1200), "passage sélectionné")
    suffix = (
        f"\n\n{other_sources}\n\n"
        f"Échanges précédents :\n{untrusted(history, 'conversation')}\n\n"
        f"Passage sélectionné :\n{selection}\n\n"
        f"Question actuelle :\n{_fit(context.question, 2400)}"
    )
    system = render_prompt(LESSON_PROFESSOR)
    prefix = "Références :\n[1] "
    title = _fit(context.source.title, 250) + "\n"
    fixed = len((system + prefix + untrusted(title, "référence") + suffix).encode())
    material = _fit(context.material, MAX_INPUT_BYTES - fixed)
    lesson = untrusted(title + material, "référence")
    return [SystemMessage(system), HumanMessage(prefix + lesson + suffix)]


def _output_budget(
    deps: GraphDeps, context: ConversationContext, messages: list[BaseMessage]
) -> int:
    spent = context.used_tokens + sum(len(message_text(msg).encode()) for msg in messages)
    cap = min(TURN_TOKEN_LIMIT, deps.settings.session_token_cap)
    available = cap - spent - TOKEN_OVERHEAD
    if available < MIN_OUTPUT_TOKENS:
        raise AppError(
            "conversation_budget_reached", "Le budget de ce tour de conversation est atteint.", 429
        )
    return min(MAX_OUTPUT_TOKENS, available)


def make_reply(deps: GraphDeps) -> Node:
    @node_timeout()
    async def reply(state: ConversationState) -> ConversationState:
        context = await deps.ports.conversations.context(
            deps.user_id, deps.session_id, state["thread_id"], state["turn_id"]
        )
        if context is None:
            return {}
        memory = await _memory_sources(deps, context.question)
        sources = [context.source, *memory]
        messages = _messages(context, memory)
        max_output = _output_budget(deps, context, messages)
        model = await deps.models.get_chat_model(
            deps.user_id, "fort" if context.strong else "rapide", agent=LESSON_PROFESSOR
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
            agent=LESSON_PROFESSOR,
            step="reponse",
            intent="J'explique la leçon.",
            catalog=catalog,
            max_words=600,
            retry=False,
        )
        answer = spoken.text[:MAX_ANSWER]
        return {
            "answer": answer,
            "sources": [
                sources[c.index - 1].model_dump(mode="json")
                for c in extract_citations(answer, catalog)
            ],
        }

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
            )
        return {"summary": "Réponse du Professeur enregistrée."}

    return save
