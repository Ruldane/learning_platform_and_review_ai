"""Draft a module's lesson from its selected, numbered and untrusted sources (SPEC 3.5, D90).

The strong model drafts and revises the lesson using feedback from the Verifier. Drafting
can be replayed without writing to storage. The lesson is saved at publication.
"""

import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.nodes.lesson_common import (
    LANGUAGES,
    Node,
    brief_of,
    lesson_sources,
    module_prompt,
    sources_prompt,
)
from app.agents.nodes.verifier.checks import MAX_WORDS, MIN_WORDS, SECTIONS
from app.agents.nodes.verifier.grades import CRITERIA, MIN_GRADE
from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import invoke_agent, message_text, node_timeout
from app.agents.runtime.played_model import refresh_updated_brief
from app.agents.state.lesson_factory import LessonFactoryState

AGENT = "writer"
WRITE_TIMEOUT_S = 600  # Allow the strong model to write up to 2,500 words, including retries.
TARGET_WORDS = 1800
MAX_PROBLEMS_SHOWN = 30
_WRAPPED = re.compile(r"\A\s*```(?:markdown|md)?[ \t]*\n(.*)\n```\s*\Z", re.DOTALL)


def unwrap(text: str) -> str:
    """Remove an outer Markdown code fence from the model's draft."""
    match = _WRAPPED.match(text)
    return (match.group(1) if match else text).strip()


def _checks(state: LessonFactoryState) -> str:
    """Wrap feedback that quotes the lesson or the model's claims as untrusted data."""
    lines = [f"- Problem: {p}" for p in state.get("problems", [])[:MAX_PROBLEMS_SHOWN]]
    lines += [f"- Unsupported claim: {c}" for c in state.get("unsupported", [])]
    return untrusted("\n".join(lines), "Verifier feedback")


def _kept(state: LessonFactoryState) -> str:
    """List the draft's passing grades to preserve during revision (D305)."""
    scores = state.get("scores", {})
    return ", ".join(
        f"{label} ({scores[name]}/100)"
        for name, label in CRITERIA.items()
        if scores.get(name, 0) >= MIN_GRADE
    )


def make_write(deps: GraphDeps) -> Node:
    @node_timeout(WRITE_TIMEOUT_S)
    async def write(state: LessonFactoryState) -> LessonFactoryState:
        brief = brief_of(state)
        previous = state.get("draft", "")
        revision = state.get("revisions", 0) + (1 if previous else 0)
        prompt = render_prompt(
            AGENT,
            title=untrusted(f"# {brief.title}", "Markdown title"),
            module=module_prompt(brief),
            sources=sources_prompt(lesson_sources(state)),
            language=LANGUAGES.get(brief.language, brief.language),
            sections=SECTIONS,
            min_words=MIN_WORDS,
            max_words=MAX_WORDS,
            target_words=TARGET_WORDS,
            previous=untrusted(previous, "previous draft") if previous else "",
            revision=revision,
            checks=_checks(state) if previous else "",
            previous_words=state.get("words", 0),
            kept=_kept(state) if previous else "",
        )
        model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
        reply = await invoke_agent(
            refresh_updated_brief(model),
            [
                SystemMessage(prompt),
                HumanMessage("Revise the lesson." if previous else "Write the lesson."),
            ],
            agent=AGENT,
            step=f"lecon-{revision}",
            intent="revising the lesson" if previous else "writing the lesson",
            expose_reply=not state.get("verification", False),
        )
        return {"draft": unwrap(message_text(reply)), "revisions": revision}

    return write
