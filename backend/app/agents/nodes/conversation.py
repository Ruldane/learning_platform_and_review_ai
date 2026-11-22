import re
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
    BRAIN_LIBRARIAN,
    TRAINING_TUTOR,
    TURN_TOKEN_LIMIT,
    ConversationContext,
    ConversationPractice,
    ConversationReference,
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
_REVISION = re.compile(
    r"^À revoir\s+\[(\d{1,2})]\s*:\s*(.{1,500}?)\s*→\s*(.{1,1000})$",
    re.MULTILINE,
)


class ConversationState(TypedDict, total=False):
    thread_id: str
    turn_id: str
    answer: str
    sources: list[dict[str, Any]]
    practice: list[dict[str, Any]]
    context_notes: dict[str, str] | None
    summary: str


class Node(Protocol):
    async def __call__(self, state: ConversationState) -> ConversationState: ...


async def _memory_sources(deps: GraphDeps, question: str) -> list[ConversationReference]:
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
    return [ConversationReference(source, source.excerpt or "") for source in sources.values()]


def _fit(text: str, limit: int) -> str:
    return text.encode()[: max(0, limit)].decode(errors="ignore")


def _catalog_text(refs: Sequence[ConversationReference], limit: int) -> str:
    def render(bodies: list[str]) -> str:
        return "\n\n".join(
            f"[{index}] {untrusted(_fit(ref.source.title, 200) + '\n' + body, 'référence')}"
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
    context: ConversationContext, refs: Sequence[ConversationReference]
) -> list[BaseMessage]:
    history = "\n".join(
        f"Question : {turn.question}\nRéponse : {turn.answer}" for turn in context.history
    )
    history = history.encode()[-650:].decode(errors="ignore")
    selection = untrusted(_fit(context.selection or "", 1200), "passage sélectionné")
    suffix = (
        f"\n\nÉchanges précédents :\n{untrusted(history, 'conversation')}\n\n"
        f"Passage sélectionné :\n{selection}\n\n"
        f"Question actuelle :\n{_fit(context.question, 2400)}"
    )
    system = render_prompt(context.agent, mode=context.mode)
    prefix = "Références :\n"
    fixed = len((system + prefix + suffix).encode())
    catalog = _catalog_text(refs, MAX_INPUT_BYTES - fixed)
    return [SystemMessage(system), HumanMessage(prefix + catalog + suffix)]


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


def make_reply(deps: GraphDeps) -> Node:
    @node_timeout()
    async def reply(state: ConversationState) -> ConversationState:
        context = await deps.ports.conversations.context(
            deps.user_id, deps.session_id, state["thread_id"], state["turn_id"]
        )
        if context is None:
            return {}
        refs = list(context.references)
        if context.agent != BRAIN_LIBRARIAN:
            refs.extend(await _memory_sources(deps, context.question))
        sources = [reference.source for reference in refs]
        messages = _messages(context, refs)
        max_output = _output_budget(deps, context, messages)
        model = await deps.models.get_chat_model(
            deps.user_id, "fort" if context.strong else "rapide", agent=context.agent
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
            intent="Je t'accompagne dans ton étude.",
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
            "practice": _practice_of(answer, sources) if context.agent == TRAINING_TUTOR else [],
            "context_notes": context.context_notes,
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
                practice=[
                    ConversationPractice.model_validate(card) for card in state.get("practice", [])
                ],
                context_notes=state.get("context_notes"),
            )
        return {"summary": "Réponse enregistrée."}

    return save
