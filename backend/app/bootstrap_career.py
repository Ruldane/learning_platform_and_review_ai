"""Composition des features de la carrière (phase 6, preflight G17) : offres et écart (D122), puis,
au fil de la phase, profil maître, gabarits et revues de CV. Gardée hors de `app.main` pour qu'il
reste court : une feature de plus = un champ de `CareerRuntimes` et une ligne dans
`career_runtimes`. Comme `app.bootstrap`, seul `app.main` l'importe (contrat 5)."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.launcher import SessionLauncher
from app.agents.tools.gap_port import GapStore
from app.features.memory.service.runtime import MemoryRuntime
from app.features.postings.service.agent_store import AgentGapStore
from app.features.postings.service.runtime import PostingsRuntime
from app.features.research.service.runtime import ResearchRuntime


@dataclass(frozen=True)
class CareerRuntimes:
    """Ce que les routes de la carrière lisent sur `app.state.career`, et les ports qu'elles
    donnent au moteur d'agents (`agent_ports`)."""

    postings: PostingsRuntime
    gap: GapStore  # port de l'Analyste (D121)


def career_runtimes(
    session_factory: async_sessionmaker[AsyncSession],
    launcher: SessionLauncher,
    *,
    research: ResearchRuntime,
    memory: MemoryRuntime,
) -> CareerRuntimes:
    """Offres (lecture du lien par la recherche web, élément `offre` et doublons par la mémoire,
    analyse lancée par le lanceur, lié au moteur ensuite) et port de l'écart."""
    postings = PostingsRuntime(session_factory, research, memory, launcher)
    return CareerRuntimes(postings=postings, gap=AgentGapStore(session_factory, memory))
