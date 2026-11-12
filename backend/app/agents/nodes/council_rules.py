"""Règles et matériel communs du débat du Conseil (SPEC 9.3, D85) : les quatre débatteurs, les
plafonds, le catalogue de citations, les tours précédents et l'objectif tels que les prompts les
montrent, et la lecture des entrées de January (messages et commandes permanentes).

Tout ce qu'un agent a écrit (tours précédents, compte rendu, propositions) et tout ce qui vient du
web ou de la mémoire (catalogue) est encadré par `untrusted()` quand un autre agent le relit
(17.4). Les textes de January (objectif, cadrage, messages) sont ses souhaits : non encadrés,
comme en D53 §5 et D84, mais jamais journalisés."""

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
DEBATERS: tuple[Debater, ...] = get_args(Debater)  # les quatre qui débattent (9.1)
NAMES: dict[str, str] = {
    "strategist": "Stratège",
    "practitioner": "Praticien",
    "scout": "Éclaireur",
    "skeptic": "Sceptique",
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
    return date.fromisoformat(raw).strftime("%d/%m/%Y") if raw else "aucune"


def goal_vars(state: CouncilState) -> dict[str, Any]:
    """Variables communes des prompts du Conseil : l'objectif et le cadrage de January."""
    goal = state["goal"]
    answers = state.get("framing_answers", {})
    framing = [
        f"- {q['question']}\n  Réponse : {answers[q['id']]}"
        for q in state.get("framing_questions", [])
        if q["id"] in answers
    ]
    return {
        "goal": goal["text"],
        "target_role": goal.get("target_role") or "non précisé",
        "deadline": deadline_text(goal),
        "weekly_minutes": goal.get("weekly_minutes"),
        "framing": "\n".join(framing) or "Aucune réponse de cadrage.",
    }


def citation_entries(state: CouncilState) -> list[CitationEntry]:
    return [
        CitationEntry(e["index"], e["title"], e.get("url"), e.get("memory_item_id"))
        for e in state.get("catalog", [])
    ]


def catalog_prompt(catalog: list[dict[str, Any]]) -> str:
    """Le catalogue numéroté : numéro hors cadre, titre et résumé encadrés."""
    if not catalog:
        return "Aucune source citable : présente tes affirmations comme ton avis."
    return "\n\n".join(
        f"[{e['index']}]\n" + untrusted(f"{e['title']}\n{e['summary']}", f"catalogue {e['index']}")
        for e in catalog
    )


def transcript_prompt(turns: list[dict[str, Any]]) -> str:
    """Tous les tours précédents, chaque prise de parole encadrée (sortie d'un autre agent)."""
    if not turns:
        return "Personne n'a encore parlé."
    return "\n\n".join(
        f"{NAMES.get(t['agent'], t['agent'])}, tour {t['round']} :\n"
        + untrusted(t["text"], f"{t['agent']} tour {t['round']}")
        for t in turns
    )


def people_prompt(state: CouncilState) -> str:
    """Praticiens repérés par l'Éclaireur (noms, rôles et sites viennent du web : encadrés)."""
    people = state.get("people", [])
    if not people:
        return "Aucun praticien repéré."
    lines = [
        f"- {one_line(p['name'])} — {one_line(p['role'])} (publie sur {', '.join(p['where'])})"
        for p in people
    ]
    return untrusted("\n".join(lines), "praticiens repérés")


def notes_prompt(notes: list[str]) -> str:
    return "\n".join(f"- {one_line(note)}" for note in notes)


def _source_entries(state: CouncilState) -> list[dict[str, Any]]:
    return [
        {"title": v["title"], "summary": v["summary"], "url": v["url"], "memory_item_id": None}
        for v in state.get("verdicts", [])
        if v["verdict"] == "kept"
    ]


async def _memory_entries(deps: GraphDeps, state: CouncilState, agent: str) -> list[dict[str, Any]]:
    """Éléments de la mémoire proches de l'objectif, hors sources (déjà au catalogue). Une
    mémoire indisponible laisse le catalogue aux seules sources (journal : session)."""
    try:
        found = await memory_search(
            deps, state["goal"]["text"], None, CATALOG_MEMORY_K, agent=agent
        )
    except AppError as exc:
        logger.warning("Catalogue sans mémoire (%s) : session %s", exc.code, deps.session_id)
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
    """Catalogue de citations, numéroté une fois pour tout le débat : sources retenues, puis
    éléments de la mémoire."""
    entries = _source_entries(state) + await _memory_entries(deps, state, agent)
    return [{"index": index, **entry} for index, entry in enumerate(entries, start=1)]


@dataclass(frozen=True)
class Absorbed:
    """Entrées de January lues depuis `last_input_seq` : textes et commandes, dans l'ordre."""

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
    """Les mêmes entrées, sans `another_round` ni `to_proposals` : envoyées pendant l'attente du
    choix, elles sont réglées par la réponse elle-même (un nouveau tour, D85)."""
    kept = [c for c in read.commands if c not in ("another_round", "to_proposals")]
    return replace(read, commands=kept)


def absorb(state: CouncilState, read: Absorbed, *, carry: bool, target: int) -> CouncilState:
    """Mise à jour de l'état pour des entrées lues. `carry` (début de tour) : garde les notes et
    l'angle déjà lus en fin de tour précédent ; sinon (fin de tour) ils sont remplacés, car le tour
    qui vient de finir les a traités. `another_round` ajoute un tour (8 au plus), `to_proposals`
    arrête le débat, `more_concrete` / `shorter` fixent l'angle du tour suivant (le dernier
    gagne). `target` : dernier tour prévu avant ces entrées."""
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
