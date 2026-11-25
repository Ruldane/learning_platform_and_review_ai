"""Common rules and material of the Council debate (SPEC 9.3, D85): the four debaters, the caps,
the citation catalog, the previous rounds and the goal as the prompts show them, and the reading
of January's inputs (messages and standing commands).

Everything an agent wrote (previous rounds, minutes, proposals) and everything that comes from the
web or from memory (catalog) is wrapped by `untrusted()` when another agent rereads it
(17.4). January's texts (goal, framing, messages) are her wishes: not wrapped,
as in D53 section 5 and D84, but never logged."""

import logging
from dataclasses import dataclass, field, replace
from datetime import date
from typing import Any, Literal, Protocol, get_args

from app.agents.prompts.loader import untrusted
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.events import UserCommand
from app.agents.runtime.speech import CitationEntry
from app.agents.state.learning_council import CouncilState
from app.agents.tools.memory_tools import memory_search
from app.core.errors import AppError

Debater = Literal["strategist", "practitioner", "scout", "skeptic"]
DEBATERS: tuple[Debater, ...] = get_args(Debater)  # the four who debate (9.1)
NAMES: dict[str, str] = {
    "strategist": "Strategist",
    "practitioner": "Practitioner",
    "scout": "Scout",
    "skeptic": "Skeptic",
}
MAX_WORDS = 150
SHORT_WORDS = 80
MAX_ROUNDS = 8
MINUTES_WORDS = 200
CATALOG_MEMORY_K = 8
CATALOG_SUMMARY_CHARS = 300
ANGLES: tuple[UserCommand, ...] = ("more_concrete", "shorter")

logger = logging.getLogger(__name__)


class Node(Protocol):
    async def __call__(self, state: CouncilState) -> CouncilState: ...


def one_line(text: str) -> str:
    return " ".join(text.split())


def deadline_text(goal: dict[str, Any]) -> str:
    raw = goal.get("deadline")
    return date.fromisoformat(raw).strftime("%d/%m/%Y") if raw else "none"


def goal_vars(state: CouncilState) -> dict[str, Any]:
    """Common variables of the Council prompts: January's goal and framing."""
    goal = state["goal"]
    answers = state.get("framing_answers", {})
    framing = [
        f"- {q['question']}\n  Answer: {answers[q['id']]}"
        for q in state.get("framing_questions", [])
        if q["id"] in answers
    ]
    return {
        "goal": goal["text"],
        "target_role": goal.get("target_role") or "not specified",
        "deadline": deadline_text(goal),
        "weekly_minutes": goal.get("weekly_minutes"),
        "framing": "\n".join(framing) or "No framing answers.",
    }


def citation_entries(state: CouncilState) -> list[CitationEntry]:
    return [
        CitationEntry(e["index"], e["title"], e.get("url"), e.get("memory_item_id"))
        for e in state.get("catalog", [])
    ]


def catalog_prompt(catalog: list[dict[str, Any]]) -> str:
    """The numbered catalog: number outside the wrapper, title and summary wrapped."""
    if not catalog:
        return "No citable source: present your claims as your opinion."
    return "\n\n".join(
        f"[{e['index']}]\n" + untrusted(f"{e['title']}\n{e['summary']}", f"catalog {e['index']}")
        for e in catalog
    )


def transcript_prompt(turns: list[dict[str, Any]]) -> str:
    """All the previous rounds, each speech wrapped (output of another agent)."""
    if not turns:
        return "Nobody has spoken yet."
    return "\n\n".join(
        f"{NAMES.get(t['agent'], t['agent'])}, round {t['round']}:\n"
        + untrusted(t["text"], f"{t['agent']} round {t['round']}")
        for t in turns
    )


def people_prompt(state: CouncilState) -> str:
    """Practitioners spotted by the Scout (names, roles and sites come from the web: wrapped)."""
    people = state.get("people", [])
    if not people:
        return "No practitioner spotted."
    lines = [
        f"- {one_line(p['name'])} — {one_line(p['role'])} (publishes on {', '.join(p['where'])})"
        for p in people
    ]
    return untrusted("\n".join(lines), "practitioners spotted")


def notes_prompt(notes: list[str]) -> str:
    return "\n".join(f"- {one_line(note)}" for note in notes)


def _source_entries(state: CouncilState) -> list[dict[str, Any]]:
    return [
        {"title": v["title"], "summary": v["summary"], "url": v["url"], "memory_item_id": None}
        for v in state.get("verdicts", [])
        if v["verdict"] == "kept"
    ]


async def _memory_entries(deps: GraphDeps, state: CouncilState, agent: str) -> list[dict[str, Any]]:
    """Memory items close to the goal, excluding sources (already in the catalog). Unavailable
    memory leaves the catalog with the sources alone (log: session)."""
    try:
        found = await memory_search(
            deps, state["goal"]["text"], None, CATALOG_MEMORY_K, agent=agent
        )
    except AppError as exc:
        logger.warning("Catalog without memory (%s): session %s", exc.code, deps.session_id)
        return []
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for hit in found.hits:
        if hit.kind == "source" or hit.item_id in seen:
            continue
        seen.add(hit.item_id)
        summary = one_line(hit.text)[:CATALOG_SUMMARY_CHARS]
        entries.append(
            {
                "title": one_line(hit.title),
                "summary": summary,
                "url": None,
                "memory_item_id": hit.item_id,
            }
        )
    return entries


async def build_catalog(
    deps: GraphDeps, state: CouncilState, *, agent: str
) -> list[dict[str, Any]]:
    """Citation catalog, numbered once for the whole debate: selected sources, then memory
    items."""
    entries = _source_entries(state) + await _memory_entries(deps, state, agent)
    return [{"index": index, **entry} for index, entry in enumerate(entries, start=1)]


@dataclass(frozen=True)
class Absorbed:
    """January's inputs read since `last_input_seq`: texts and commands, in order."""

    last_seq: int
    texts: list[str] = field(default_factory=list)
    commands: list[UserCommand] = field(default_factory=list)


async def read_inputs(deps: GraphDeps, state: CouncilState) -> Absorbed:
    last = state.get("last_input_seq", 0)
    inputs = await deps.user_inputs_since(last)
    return Absorbed(
        last_seq=inputs[-1].seq if inputs else last,
        texts=[text for i in inputs if (text := i.text.strip())],
        commands=[i.command for i in inputs if i.command is not None],
    )


def without_round_commands(read: Absorbed) -> Absorbed:
    """The same inputs, without `another_round` or `to_proposals`: sent while waiting for the
    choice, they are settled by the answer itself (a new round, D85)."""
    kept = [c for c in read.commands if c not in ("another_round", "to_proposals")]
    return replace(read, commands=kept)


def absorb(state: CouncilState, read: Absorbed, *, carry: bool, target: int) -> CouncilState:
    """State update for the inputs read. `carry` (start of round): keeps the notes and the angle
    already read at the end of the previous round; otherwise (end of round) they are replaced,
    because the round that just ended handled them. `another_round` adds a round (8 at most),
    `to_proposals` stops the debate, `more_concrete` / `shorter` set the angle of the next round
    (the last one wins). `target`: last round planned before these inputs."""
    target = min(target + read.commands.count("another_round"), MAX_ROUNDS)
    angles = [c for c in read.commands if c in ANGLES]
    angle = angles[-1] if angles else (state.get("angle") if carry else None)
    kept_notes = state.get("round_notes", []) if carry else []
    return {
        "last_input_seq": read.last_seq,
        "notes": read.texts,
        "round_notes": [*kept_notes, *read.texts],
        "rounds_target": target,
        "angle": angle,
        "stop": bool(state.get("stop")) or "to_proposals" in read.commands,
    }


def debate_over(state: CouncilState) -> bool:
    return bool(state.get("stop")) or state.get("round", 0) >= state.get("rounds_target", 1)
