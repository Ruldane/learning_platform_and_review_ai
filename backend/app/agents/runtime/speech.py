"""Prise de parole citée et bornée, pour le débat du Conseil (SPEC 9.3, D82).

Le plafond de mots est imposé par le code après le flux : les tokens arrivent en direct, puis
`agent.message` porte le texte coupé et ses citations, avec le même `message_id`, donc la bulle
finale remplace celle des tokens (D57). Les citations sont les marqueurs `[n]` du texte qui
renvoient à un catalogue numéroté (sources récupérées, éléments de la mémoire).
"""

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from app.agents.runtime.emit import emit
from app.agents.runtime.events import AgentMessagePayload, Citation
from app.agents.runtime.invoke import call_with_retries, message_text

ELLIPSIS = "…"
_TOKEN = re.compile(r"\S+")
_MARKER = re.compile(r"\[(\d{1,4}(?:\s*,\s*\d{1,4})*)\]")
_LETTER_OR_DIGIT = re.compile(r"\w")
# Marqueur entier ou morceau d'un marqueur coupé par une espace (`[2,` puis `3]`).
_MARKER_PART = re.compile(r"\[[\d,]*\]?|^[\d,]*\]")
# Fin de phrase : « . », « ! » ou « ? », suivis au plus de fermants ou d'un marqueur `[n]`.
_SENTENCE_END = re.compile(r"[.!?][\"'»”)\]*_]*(?:\[[\d,\s]+\])?[\"'»”)]*$")
# Jeton qui prolonge une fin de phrase : fermants seuls ou marqueur `[n]` séparé par une espace
# (`aide. [1]`, `aide. [1, 2]`), pour ne jamais perdre une citation à la coupe.
_TRAILING = re.compile(r"^(?:\[[\d,]*\]?|[\d,]*\]|[\"'»”)\]])+$")


@dataclass(frozen=True)
class CitationEntry:
    """Une entrée du catalogue montré à l'agent : `[index] titre`."""

    index: int
    title: str
    url: str | None = None
    memory_item_id: str | None = None


@dataclass(frozen=True)
class Spoken:
    text: str
    citations: list[Citation]
    words: int
    revised: bool = False  # une nouvelle demande a été faite (`revise`)


def _is_word(token: str) -> bool:
    """Un mot contient une lettre ou un chiffre ; un marqueur `[n]` n'en est pas un."""
    return bool(_LETTER_OR_DIGIT.search(_MARKER_PART.sub("", token)))


def count_words(text: str) -> int:
    return sum(1 for match in _TOKEN.finditer(text) if _is_word(match.group()))


def cap_words(text: str, limit: int) -> str:
    """`limit` mots au plus : texte inchangé s'il tient ; sinon coupé après la dernière phrase
    complète (., !, ?) qui tient dans `limit` mots, à défaut après les `limit` premiers mots
    suivis de « … ». La mise en forme (sauts de ligne) de la partie gardée est conservée."""
    if count_words(text) <= limit:
        return text
    words = 0
    word_end = sentence_end = 0
    previous_end = -1
    for match in _TOKEN.finditer(text):
        token = match.group()
        if _is_word(token):
            words += 1
            if words > limit:
                break
            word_end = match.end()
        if _SENTENCE_END.search(token) or (_TRAILING.match(token) and sentence_end == previous_end):
            sentence_end = match.end()
        previous_end = match.end()
    if sentence_end:
        return text[:sentence_end]
    return f"{text[:word_end].rstrip()} {ELLIPSIS}"


def extract_citations(text: str, catalog: Sequence[CitationEntry]) -> list[Citation]:
    """Citations des marqueurs `[n]` (et `[n, m]`) connus du catalogue, dans l'ordre
    d'apparition, sans doublon ; un numéro inconnu est ignoré (jamais une citation inventée)."""
    by_index = {entry.index: entry for entry in catalog}
    seen: set[int] = set()
    found: list[Citation] = []
    for match in _MARKER.finditer(text):
        for part in match.group(1).split(","):
            entry = by_index.get(int(part))
            if entry is None or entry.index in seen:
                continue
            seen.add(entry.index)
            found.append(
                Citation(
                    index=entry.index,
                    title=entry.title,
                    url=entry.url,
                    memory_item_id=entry.memory_item_id,
                )
            )
    return found


async def speak(
    model: BaseChatModel,
    messages: list[BaseMessage],
    *,
    agent: str,
    step: str,
    intent: str,
    catalog: Sequence[CitationEntry],
    max_words: int,
    revise: Callable[[str], str | None] | None = None,
) -> Spoken:
    """`agent.started`, tokens en direct (`call_with_retries`), puis `agent.message` avec le
    texte coupé à `max_words` et ses citations, sous le `message_id` des tokens (D57).

    `revise(texte coupé)` rend une demande de correction (règles du débat non tenues, D85) ou
    `None` : une seule nouvelle demande est faite alors, sans tokens en direct, et son texte
    remplace le premier sous le même `message_id` (la bulle en cours est corrigée)."""
    emit("agent.started", {"step": step, "intent": intent}, agent=agent)
    reply = await call_with_retries(model, messages, agent=agent)
    text = cap_words(message_text(reply).strip(), max_words)
    correction = revise(text) if revise is not None else None
    if correction is not None:
        retry = [*messages, AIMessage(text), HumanMessage(correction)]
        second = await call_with_retries(model, retry, agent=agent, stream=False)
        text = cap_words(message_text(second).strip(), max_words)
    citations = extract_citations(text, catalog)
    payload = AgentMessagePayload(
        message_id=reply.id or f"{agent}-{step}", text=text, citations=citations
    )
    emit("agent.message", payload, agent=agent)
    return Spoken(
        text=text, citations=citations, words=count_words(text), revised=correction is not None
    )
