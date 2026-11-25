"""An agent's memory context (SPEC 4.4), reusable by any flow: known skills, decisions and
documents close to the objective. Each read is a visible tool call (`tool.called` /
`tool.result`). The port already wraps the fragments as untrusted."""

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
            f"What January can already do:\n{self.skills.as_agent_text()}\n\n"
            f"Past decisions close to the objective:\n{self.decisions.agent_text}\n\n"
            f"January's documents close to the objective:\n{self.documents.agent_text}"
        )


async def load_memory_context(deps: GraphDeps, *, objective: str, agent: str) -> MemoryContext:
    """Skills, then decisions and documents close to `objective` (8 fragments each). A missing
    or stopped memory raises the port's `AppError`: the calling node decides."""
    skills = await memory_get_skills(deps, agent=agent)
    decisions = await memory_search(deps, objective, ["decision"], CONTEXT_K, agent=agent)
    documents = await memory_search(deps, objective, ["document"], CONTEXT_K, agent=agent)
    return MemoryContext(skills, decisions, documents)
