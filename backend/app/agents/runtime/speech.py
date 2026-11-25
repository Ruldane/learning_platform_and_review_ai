"""Quoted and bounded speech, for the Council's debate (SPEC 9.3, D82).

The word cap is enforced by the code after the stream: tokens arrive live, then
`agent.message` carries the cut text and its citations, with the same `message_id`, so the final
bubble replaces the tokens' one (D57). Citations are the `[n]` markers in the text that
point to a numbered catalog (retrieved sources, memory items).
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
# Whole marker, or piece of a marker split by a space (`[2,` then `3]`).
_MARKER_PART = re.compile(r"\[[\d,]*\]?|^[\d,]*\]")
# End of sentence: ".", "!" or "?", followed at most by closers or a `[n]` marker.
_SENTENCE_END = re.compile(r"[.!?][\"'»”)\]*_]*(?:\[[\d,\s]+\])?[\"'»”)]*$")
# Token that extends a sentence end: closers alone or a `[n]` marker split by a space
# (`aide. [1]`, `aide. [1, 2]`), so a citation is never lost at the cut.
_TRAILING = re.compile(r"^(?:\[[\d,]*\]?|[\d,]*\]|[\"'»”)\]])+$")


@dataclass(frozen=True)
class CitationEntry:
    """An entry of the catalog shown to the agent: `[index] title`."""

    index: int
    title: str
    url: str | None = None
    memory_item_id: str | None = None


@dataclass(frozen=True)
class Spoken:
    text: str
    citations: list[Citation]
    words: int
    revised: bool = False  # a new request was made (`revise`)


def _is_word(token: str) -> bool:
    """A word contains a letter or a digit; a `[n]` marker is not one."""
    return bool(_LETTER_OR_DIGIT.search(_MARKER_PART.sub("", token)))


def count_words(text: str) -> int:
    return sum(1 for match in _TOKEN.finditer(text) if _is_word(match.group()))


def _cut_at(text: str, limit: int) -> tuple[int, bool]:
    """End of the kept part of `text` (over `limit` words) and whether "…" follows: the
    last complete sentence (., !, ?) that fits, otherwise the first `limit` words."""
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
    return (sentence_end, False) if sentence_end else (word_end, True)


def _cut(text: str, limit: int) -> str:
    end, ellipsis = _cut_at(text, limit)
    return f"{text[:end].rstrip()} {ELLIPSIS}" if ellipsis else text[:end]


def _keep_line(text: str, limit: int, keep: re.Pattern[str]) -> str | None:
    """Cut that keeps whole the first line where `keep` matches (counted in `limit`),
    or `None` if no line matches or if the ordinary cut already keeps it."""
    match = keep.search(text)
    if match is None or match.end() == match.start():
        return None
    # The line is the one where the match ENDS: a pattern that allows leading blanks
    # (`^\s*` in MULTILINE) can start on an empty line above (review 5.1, I1).
    anchor = match.end() - 1
    start = text.rfind("\n", 0, anchor) + 1
    stop = text.find("\n", anchor)
    stop = len(text) if stop == -1 else stop
    if _cut_at(text, limit)[0] >= stop:
        return None
    line = text[start:stop].rstrip()
    room = limit - count_words(line)
    if room <= 0:
        return _cut(line, limit) if room < 0 else line
    before = text[:start].rstrip()
    if not before:
        return line
    head = before if count_words(before) <= room else _cut(before, room)
    return f"{head}\n{line}"


def cap_words(text: str, limit: int, *, keep: re.Pattern[str] | None = None) -> str:
    """`limit` words at most: text unchanged if it fits; otherwise cut after the last complete
    sentence (., !, ?) that fits in `limit` words, otherwise after the first `limit` words
    followed by "…". The formatting (line breaks) of the kept part is preserved.

    With `keep`, the first matching line is kept whole (counted in `limit`,
    cut only if it alone exceeds `limit`): what precedes it is cut as above
    within the remaining words, what follows it is removed (the Skeptic's objection)."""
    if count_words(text) <= limit:
        return text
    if keep is not None and (kept := _keep_line(text, limit, keep)) is not None:
        return kept
    return _cut(text, limit)


def extract_citations(text: str, catalog: Sequence[CitationEntry]) -> list[Citation]:
    """Citations of the `[n]` (and `[n, m]`) markers known to the catalog, in order
    of appearance, without duplicates; an unknown number is ignored (never an invented citation)."""
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
    keep: re.Pattern[str] | None = None,
    retry: bool = True,
) -> Spoken:
    """`agent.started`, live tokens (`call_with_retries`), then `agent.message` with the
    text cut at `max_words` and its citations, under the tokens' `message_id` (D57).

    `revise(cut text)` returns a correction request (debate rules not met, D85) or
    `None`: a single new request is then made, without live tokens, and its text
    replaces the first under the same `message_id` (the current bubble is corrected).

    `keep`: the first matching line survives the cut (`cap_words`)."""
    emit("agent.started", {"step": step, "intent": intent}, agent=agent)
    reply = await call_with_retries(model, messages, agent=agent, retry=retry)
    text = cap_words(message_text(reply).strip(), max_words, keep=keep)
    correction = revise(text) if revise is not None else None
    if correction is not None:
        revision = [*messages, AIMessage(text), HumanMessage(correction)]
        second = await call_with_retries(model, revision, agent=agent, stream=False, retry=retry)
        text = cap_words(message_text(second).strip(), max_words, keep=keep)
    citations = extract_citations(text, catalog)
    payload = AgentMessagePayload(
        message_id=reply.id or f"{agent}-{step}", text=text, citations=citations
    )
    emit("agent.message", payload, agent=agent)
    return Spoken(
        text=text, citations=citations, words=count_words(text), revised=correction is not None
    )
