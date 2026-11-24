"""Exact text an agent receives from a memory search (`memory_search` tool, test bench of the
Memory screen). Everything coming from a document or a write is untrusted content (17.4):
the title (collapsed to one line) and the text of a chunk are framed together by `untrusted`,
which strips any markers they carry. Outside the frame remain only the kind, the author
(`user` or an agent name) and the score. The query, written by the agent or by January, is
collapsed to one line and stripped of any run of three `<` or `>`."""

import re
from collections.abc import Sequence

from app.agents.prompts.loader import untrusted
from app.features.memory.schemas import SearchHitOut

_ANGLE_RUNS = re.compile(r"<{3,}|>{3,}")


def _one_line(text: str) -> str:
    return " ".join(text.split())


def _inline(text: str) -> str:
    """A single line, without any run of three `<` or `>` (loop: removing a run can bring
    two others together)."""
    text = _one_line(text)
    while (stripped := _ANGLE_RUNS.sub("", text)) != text:
        text = stripped
    return text


def format_for_agent(query: str, hits: Sequence[SearchHitOut]) -> str:
    shown = _inline(query)
    if not hits:
        return f'Memory — no chunk for "{shown}".'
    lines = [f'Memory — {len(hits)} chunk(s) for "{shown}":']
    for number, hit in enumerate(hits, start=1):
        lines.append(
            f"[{number}] {hit.kind} · author {_inline(hit.created_by)} · score {hit.score:.2f}"
        )
        framed = f"Title: {_one_line(hit.title)}\n{hit.text}"
        lines.append(untrusted(framed, f"memory:{hit.kind}"))
    return "\n".join(lines)
