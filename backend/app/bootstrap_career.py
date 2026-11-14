"""Composition des features de la carrière (phase 6, preflight G17) : offres et écart (D122), puis,
au fil de la phase, profil maître, gabarits et revues de CV. Gardée hors de `app.main` pour qu'il
reste court : une feature de plus = un champ de `CareerRuntimes` et une ligne dans
`career_runtimes`. Comme `app.bootstrap`, seul `app.main` l'importe (contrat 5)."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.launcher import SessionLauncher
from app.agents.tools.cv_template_port import CvTemplateStore
from app.agents.tools.gap_port import GapStore
from app.agents.tools.profile_port import ProfileStore
from app.core.providers import PublishingProviders
from app.features.cv.service.profile_store import AgentProfileStore
from app.features.cv.service.runtime import CvRuntime
from app.features.cv.service.templates_store import AgentCvTemplateStore
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
    cv: CvRuntime  # profil maître (D124), gabarits (D126)
    profile: ProfileStore  # port de l'Archiviste en mode `profile` (D124)
    cv_templates: CvTemplateStore  # port du Maquettiste en mode `design` (D125, D126)


def career_runtimes(
    session_factory: async_sessionmaker[AsyncSession],
    launcher: SessionLauncher,
    *,
    research: ResearchRuntime,
    memory: MemoryRuntime,
    publishing: PublishingProviders,
) -> CareerRuntimes:
    """Offres (lecture du lien par la recherche web, élément `offre` et doublons par la mémoire,
    analyse lancée par le lanceur, lié au moteur ensuite) et port de l'écart ; profil maître
    (documents rangés par la mémoire, PDF relus par la mise en page, capture lancée par le
    lanceur) et port de l'Archiviste ; gabarits (mise en page, rendu de nos gabarits HTML, polices
    libres, images et polices rangées par le stockage de la mémoire) et port du Maquettiste."""
    postings = PostingsRuntime(session_factory, research, memory, launcher)
    cv = CvRuntime(
        session_factory, memory, launcher, publishing.layout, publishing.html_pdf, publishing.fonts
    )
    return CareerRuntimes(
        postings=postings,
        gap=AgentGapStore(session_factory, memory),
        cv=cv,
        profile=AgentProfileStore(cv),
        cv_templates=AgentCvTemplateStore(cv),
    )
