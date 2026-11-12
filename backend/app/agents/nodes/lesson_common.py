"""Ce que partagent les nœuds du parcours `lesson_factory` : la forme d'un nœud et les sources
retenues, numérotées. Une source est admise dans une leçon si elle est lue et notée 60 ou plus
(SPEC 10.3) : ce sont les verdicts « kept » de la session, jamais une adresse écrite par un
modèle."""

from dataclasses import dataclass
from typing import Any, Protocol

from app.agents.nodes.scout.models import one_line, page_title
from app.agents.prompts.loader import untrusted
from app.agents.state.lesson_factory import LessonFactoryState
from app.agents.tools.lesson_port import ModuleBrief

MAX_LESSON_SOURCES = 8  # les mieux notées, pour garder un prompt de taille raisonnable
LANGUAGES = {"fr": "français", "en": "anglais"}  # nom de la langue des leçons, pour les prompts
SOURCE_CHARS = 6000  # texte lu rendu au Rédacteur et au Vérificateur, par source


class Node(Protocol):
    async def __call__(self, state: LessonFactoryState) -> LessonFactoryState: ...


@dataclass(frozen=True)
class LessonSource:
    number: int
    source_id: str
    title: str
    url: str
    score: int
    text: str


def kept_verdicts(state: LessonFactoryState) -> list[dict[str, Any]]:
    """Sources retenues de la session (note 60 ou plus), les mieux notées d'abord."""
    kept = [v for v in state.get("verdicts", []) if v["verdict"] == "kept"]
    return sorted(kept, key=lambda v: -(v["score"] or 0))  # tri stable : ordre de lecture


def lesson_sources(state: LessonFactoryState) -> list[LessonSource]:
    """Sources de la leçon : retenues, lues, numérotées de 1 à `MAX_LESSON_SOURCES`."""
    pages = {p["source_id"]: p for p in state.get("pages", []) if p.get("source_id")}
    sources: list[LessonSource] = []
    for verdict in kept_verdicts(state):
        page = pages.get(verdict["source_id"])
        if page is None or len(sources) == MAX_LESSON_SOURCES:
            continue
        sources.append(
            LessonSource(
                number=len(sources) + 1,
                source_id=verdict["source_id"],
                title=page_title(page),
                url=page["url"],
                score=verdict["score"],
                text=page["text"][:SOURCE_CHARS],
            )
        )
    return sources


def sources_prompt(sources: list[LessonSource]) -> str:
    """Chaque source encadrée comme non fiable (titre, adresse et texte viennent du web)."""
    blocks = []
    for source in sources:
        body = f"Titre : {one_line(source.title)}\nAdresse : {source.url}\n\n{source.text}"
        blocks.append(f"[{source.number}]\n{untrusted(body, f'source {source.number}')}")
    return "\n\n".join(blocks)


def module_prompt(brief: ModuleBrief) -> str:
    """La fiche du module vient du programme (sortie d'agent) : donnée encadrée, pas consigne."""
    lines = [
        f"Titre : {brief.title}",
        f"Compétences visées : {', '.join(brief.skills) or 'aucune précisée'}",
        f"Prérequis : {', '.join(brief.prerequisites) or 'aucun'}",
        f"Semaine {brief.week_rank} : {brief.week_theme}",
        f"Objectif de January : {brief.goal_text}",
    ]
    return untrusted("\n".join(lines), "module")


def brief_of(state: LessonFactoryState) -> ModuleBrief:
    data = state["brief"]
    return ModuleBrief(
        module_id=data["module_id"],
        program_id=data["program_id"],
        title=data["title"],
        skills=tuple(data["skills"]),
        prerequisites=tuple(data["prerequisites"]),
        week_rank=data["week_rank"],
        week_theme=data["week_theme"],
        goal_text=data["goal_text"],
        language=data["language"],
        seed_urls=tuple(data["seed_urls"]),
    )
