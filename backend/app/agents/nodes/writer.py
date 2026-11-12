"""Le Rédacteur écrit la leçon d'un module (SPEC 3.5, D90) à partir des sources retenues,
numérotées et encadrées comme non fiables ; le modèle fort écrit, le Vérificateur contrôle.

`write` est rejoué comme les autres : il ne touche aucun port, la leçon n'est écrite en base
qu'à la publication. Une révision (au plus `MAX_REVISIONS`) reçoit le brouillon précédent, les
problèmes des contrôles (« Problème : … ») et les affirmations non sourcées (« Affirmation non
sourcée : … »)."""

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
from app.agents.prompts.loader import render_prompt, untrusted
from app.agents.registry import get_agent
from app.agents.runtime.deps import GraphDeps
from app.agents.runtime.invoke import invoke_agent, message_text, node_timeout
from app.agents.state.lesson_factory import LessonFactoryState

AGENT = "writer"
WRITE_TIMEOUT_S = 600  # une leçon de 2 500 mots au modèle fort, avec ses nouveaux essais
TARGET_WORDS = 1800
MAX_PROBLEMS_SHOWN = 30
_WRAPPED = re.compile(r"\A\s*```(?:markdown|md)?[ \t]*\n(.*)\n```\s*\Z", re.DOTALL)


def unwrap(text: str) -> str:
    """La leçon sans la balise de code dont un modèle l'enveloppe parfois."""
    match = _WRAPPED.match(text)
    return (match.group(1) if match else text).strip()


def make_write(deps: GraphDeps) -> Node:
    @node_timeout(WRITE_TIMEOUT_S)
    async def write(state: LessonFactoryState) -> LessonFactoryState:
        brief = brief_of(state)
        previous = state.get("draft", "")
        revision = state.get("revisions", 0) + (1 if previous else 0)
        prompt = render_prompt(
            AGENT,
            title=brief.title,
            module=module_prompt(brief),
            sources=sources_prompt(lesson_sources(state)),
            language=LANGUAGES.get(brief.language, brief.language),
            sections=SECTIONS,
            min_words=MIN_WORDS,
            max_words=MAX_WORDS,
            target_words=TARGET_WORDS,
            previous=untrusted(previous, "version précédente") if previous else "",
            revision=revision,
            problems=state.get("problems", [])[:MAX_PROBLEMS_SHOWN] if previous else [],
            unsupported=state.get("unsupported", []) if previous else [],
        )
        model = await deps.models.get_chat_model(deps.user_id, get_agent(AGENT).tier, agent=AGENT)
        reply = await invoke_agent(
            model,
            [
                SystemMessage(prompt),
                HumanMessage("Corrige la leçon." if previous else "Écris la leçon."),
            ],
            agent=AGENT,
            step=f"lecon-{revision}",
            intent="je corrige la leçon" if previous else "j'écris la leçon",
        )
        return {"draft": unwrap(message_text(reply)), "revisions": revision}

    return write
