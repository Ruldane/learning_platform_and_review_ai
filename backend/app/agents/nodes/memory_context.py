"""Contexte mémoire d'un agent (SPEC 4.4), réutilisable par tout parcours : acquis connus,
décisions et documents proches de l'objectif. Chaque lecture est un appel d'outil visible
(`tool.called` / `tool.result`). Les fragments sont déjà encadrés comme non fiables par le port."""

from dataclasses import dataclass

from app.agents.runtime.deps import GraphDeps
from app.agents.tools.memory_port import MemorySearchResult, SkillsSummary
from app.agents.tools.memory_tools import memory_get_skills, memory_search

CONTEXT_K = 8


@dataclass(frozen=True)
class MemoryContext:
    skills: SkillsSummary
    decisions: MemorySearchResult
    documents: MemorySearchResult

    def as_prompt(self) -> str:
        return (
            f"Ce que January sait déjà faire :\n{self.skills.as_agent_text()}\n\n"
            f"Décisions passées proches de l'objectif :\n{self.decisions.agent_text}\n\n"
            f"Documents de January proches de l'objectif :\n{self.documents.agent_text}"
        )


async def load_memory_context(deps: GraphDeps, *, objective: str, agent: str) -> MemoryContext:
    """Acquis, puis décisions et documents proches de `objective` (8 fragments chacun). Une
    mémoire absente ou arrêtée lève l'`AppError` du port : le nœud appelant décide."""
    skills = await memory_get_skills(deps, agent=agent)
    decisions = await memory_search(deps, objective, ["decision"], CONTEXT_K, agent=agent)
    documents = await memory_search(deps, objective, ["document"], CONTEXT_K, agent=agent)
    return MemoryContext(skills, decisions, documents)
