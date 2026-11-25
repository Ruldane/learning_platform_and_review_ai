"""Career features wiring (phase 6, preflight G17): offers and gap (D122), then, as the phase
goes on, master profile, templates and CV reviews. Kept out of `app.main` so that it stays
short: one more feature = one field of `CareerRuntimes` and one line in `career_runtimes`.
As with `app.bootstrap`, only `app.main` imports it (contract 5)."""

from collections.abc import Callable
from dataclasses import dataclass

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.runtime.launcher import SessionLauncher
from app.agents.tools.applications_port import ApplicationStore
from app.agents.tools.committee_port import CommitteeStore
from app.agents.tools.cv_review_port import CvReviewStore
from app.agents.tools.cv_template_port import CvTemplateStore
from app.agents.tools.gap_port import GapStore
from app.agents.tools.interview_port import InterviewStore
from app.agents.tools.kit_port import KitStore
from app.agents.tools.profile_port import ProfileStore
from app.core.portfolio_urls import no_origin
from app.core.providers import MemoryProviders, PublishingProviders
from app.features.applications.service.agent_store import AgentApplicationStore
from app.features.applications.service.committee_store import AgentCommitteeStore
from app.features.applications.service.interview_store import AgentInterviewStore
from app.features.applications.service.kit_store import AgentKitStore
from app.features.applications.service.runtime import ApplicationsRuntime
from app.features.cv.service.profile_store import AgentProfileStore
from app.features.cv.service.review_store import AgentCvReviewStore
from app.features.cv.service.runtime import CvRuntime
from app.features.cv.service.templates_store import AgentCvTemplateStore
from app.features.memory.service.runtime import MemoryRuntime
from app.features.portfolio.service.runtime import PortfolioRuntime
from app.features.postings.service.agent_store import AgentGapStore
from app.features.postings.service.runtime import KeyLocks, PostingsRuntime
from app.features.research.service.runtime import ResearchRuntime


@dataclass(frozen=True)
class CareerRuntimes:
    """What the career routes read from `app.state.career`, and the ports they give to the agent
    engine (`agent_ports`)."""

    postings: PostingsRuntime
    gap: GapStore  # Analyst port (D121)
    cv: CvRuntime  # master profile (D124), templates (D126), reviews and versions (D130)
    profile: ProfileStore  # Archivist port in `profile` mode (D124)
    cv_templates: CvTemplateStore  # Mockup-designer port in `design` mode (D125, D126)
    cv_review: CvReviewStore  # `cv_review` flow port (D129, D130)
    applications: ApplicationsRuntime  # fiches, fil, doublons, indicateurs (D139)
    application_store: ApplicationStore  # Tracking Assistant port (D141)
    kit_store: KitStore  # `application_kit` flow port (D142, D143)
    interview_store: InterviewStore  # `interview` flow port (D145, D146)
    committee_store: CommitteeStore  # `hiring_committee` flow port (D147)


def career_runtimes(
    session_factory: async_sessionmaker[AsyncSession],
    launcher: SessionLauncher,
    *,
    research: ResearchRuntime,
    memory: MemoryRuntime,
    publishing: PublishingProviders,
    portfolio_origin: Callable[[], str | None] = no_origin,
) -> CareerRuntimes:
    """Offers (reading the link through web search, `offer` element and duplicates through memory,
    analysis launched by the launcher, linked to the engine later) and gap port; master profile
    (documents stored by memory, PDFs reread by the layout, capture launched by the launcher)
    and Archivist port; templates (layout, rendering of our HTML templates, free fonts, images
    and fonts stored by the memory storage) and Mockup-designer port; reviews (launched and
    resumed by the launcher) and port of the `cv_review` flow; applications (base, launcher,
    locks), Tracking Assistant port (one-sentence creation), application kit port and mock
    interview port."""
    postings = PostingsRuntime(session_factory, research, memory, launcher)
    company_locks = KeyLocks()  # one company record per key, reviews and kit together
    cv = CvRuntime(
        session_factory,
        memory,
        launcher,
        publishing.layout,
        publishing.html_pdf,
        publishing.fonts,
        resumer=launcher,  # « Générer le PDF » resumes the output question (D130)
        company_locks=company_locks,
        portfolio_origin=portfolio_origin,
    )
    applications = ApplicationsRuntime(
        session_factory, launcher, company_locks=company_locks, portfolio_origin=portfolio_origin
    )
    return CareerRuntimes(
        postings=postings,
        gap=AgentGapStore(session_factory, memory),
        cv=cv,
        profile=AgentProfileStore(cv),
        cv_templates=AgentCvTemplateStore(cv),
        cv_review=AgentCvReviewStore(cv),
        applications=applications,
        application_store=AgentApplicationStore(applications),
        kit_store=AgentKitStore(applications),
        interview_store=AgentInterviewStore(applications),
        committee_store=AgentCommitteeStore(applications),
    )


def compose_portfolio(app: FastAPI, providers: MemoryProviders) -> None:
    app.state.portfolio = PortfolioRuntime(
        app.state.session_factory,
        providers.storage,
        app.state.cipher,
        lambda: app.state.settings.portfolio_public_origin,
    )
