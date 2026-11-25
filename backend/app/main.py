from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents.runtime.deps import ChatModelSource
from app.agents.runtime.launcher import SessionLauncher
from app.agents.runtime.lifespan import agent_runtime
from app.agents.runtime.openapi import register_event_schemas
from app.bootstrap import (
    StudyRuntimes,
    agent_ports,
    build_providers,
    compose_phase10,
    key_test_http,
    lessons_runtime,
    model_prices,
    open_memory_runtime,
    open_research_runtime,
    run_settings_source,
    scheduler_context,
    study_runtimes,
)
from app.bootstrap import memory_providers as open_memory_providers
from app.bootstrap import publishing_providers as open_publishing_providers
from app.bootstrap import research_providers as open_research_providers
from app.bootstrap_auth import ensure_local_user, open_oidc, setup_security
from app.bootstrap_calendar import open_calendar
from app.bootstrap_career import career_runtimes, compose_portfolio
from app.bootstrap_daily import daily_runtimes
from app.bootstrap_ide import start_ide_gateway
from app.config import Settings, get_settings
from app.core.body_limits import add_body_limits
from app.core.errors import register_error_handlers
from app.core.played import RunSourceHeader
from app.core.portfolio_host import PortfolioPublicHostGuard
from app.core.providers import MemoryProviders, PublishingProviders, ResearchProviders
from app.db.engine import create_engine, create_session_factory
from app.features.auth.service.authenticator import build_authenticator
from app.features.auth.service.startup import check_google_config
from app.features.book.service.runtime import BookRuntime
from app.features.boss.service.review import AgentBossReview
from app.features.contributions.service.runtime import ContributionRuntime
from app.features.learning.service.runtime import LearningRuntime
from app.features.program.service.runtime import ProgramRuntime
from app.features.registry import FEATURE_ROUTERS
from app.features.voice.service import VoiceService
from app.providers.github.public import PublicGithub
from app.providers.speech.transcription import OpenAITranscription
from app.scheduler.registry import JOBS
from app.scheduler.runner import open_scheduler

API_PREFIX = "/api/v1"
_PROBE_TIMEOUT_SECONDS = 3.0


async def _open_external_providers(app: FastAPI, stack: AsyncExitStack) -> MemoryProviders:
    """Memory providers, then web search, then the PDF providers of our templates (D89): the ones
    that
    were injected (tests), otherwise the real composition, closed by the stack. Search reuses the
    memory web reader. Returns the memory providers."""
    memory: MemoryProviders | None = app.state.injected_memory_providers
    if memory is None:
        memory = await stack.enter_async_context(open_memory_providers(app.state.settings))
    app.state.memory_providers = memory
    research: ResearchProviders | None = app.state.injected_research_providers
    if research is None:
        research = await stack.enter_async_context(
            open_research_providers(app.state.settings, memory.web)
        )
    app.state.research_providers = research
    publishing: PublishingProviders | None = app.state.injected_publishing_providers
    if publishing is None:
        publishing = await stack.enter_async_context(open_publishing_providers(app.state.settings))
    app.state.publishing_providers = publishing
    return memory


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    check_google_config(app.state.settings)  # Google mode misconfigured: refuse to start (P11)
    setup_security(app)
    # The schema is never created here: in Docker, the entrypoint runs `alembic upgrade head`.
    # The stack closes the engine and the HTTP client even if the composition or startup fails.
    async with AsyncExitStack() as stack:
        engine = create_engine(app.state.settings.database_url)
        stack.push_async_callback(engine.dispose)
        app.state.engine = engine
        app.state.session_factory = create_session_factory(engine)
        app.state.calendar = await open_calendar(app, stack)
        # Client shared by the health probes; the Brave key test has its own (D74).
        http = await stack.enter_async_context(httpx.AsyncClient(timeout=_PROBE_TIMEOUT_SECONDS))
        key_http = await stack.enter_async_context(key_test_http())
        oidc = await open_oidc(app.state.settings, stack)
        app.state.providers = build_providers(
            app.state.settings,
            app.state.session_factory,
            app.state.cipher,
            http,
            lambda: getattr(app.state, "local_user_id", None),
            key_http=key_http,
            oidc=oidc,
        )
        if app.state.providers.embedding is not None:  # shutdown cancels the bge-m3 download
            stack.push_async_callback(app.state.providers.embedding.aclose)
        # Before memory: its worker re-reads the database at startup; a missing schema must give
        # the `alembic upgrade head` hint rather than a raw SQL error.
        if app.state.settings.auth_mode == "local":
            await ensure_local_user(app)
        app.state.authenticator = build_authenticator(
            app.state.settings, app.state.session_factory, getattr(app.state, "local_user_id", None)
        )
        injected = await _open_external_providers(app, stack)
        # Memory: entered before the agent engine (which will use it), so closed after it.
        app.state.memory = await stack.enter_async_context(
            open_memory_runtime(app.state.session_factory, injected)
        )
        # Web search: after memory (same web reader), before the agent engine.
        app.state.research = await stack.enter_async_context(
            open_research_runtime(
                app.state.session_factory, app.state.research_providers, app.state.providers
            )
        )
        compose_portfolio(app, injected)
        await _open_agents(app, stack)
        app.state.voice = VoiceService(
            OpenAITranscription(app.state.research.keys), app.state.daily.podcast.speech
        )
        yield


def _compose_features(app: FastAPI) -> StudyRuntimes:
    """Composes the services before linking their launcher to the agent engine."""
    app.state.launcher = SessionLauncher()
    app.state.learning = LearningRuntime(app.state.session_factory, app.state.launcher)
    app.state.lessons = lessons_runtime(
        app.state.session_factory,
        app.state.launcher,
        memory=app.state.memory,
        research=app.state.research,
        files=app.state.memory_providers,
        publishing=app.state.publishing_providers,
    )
    app.state.program = ProgramRuntime(
        app.state.session_factory, app.state.memory, lessons=app.state.lessons
    )
    app.state.book = BookRuntime(
        app.state.session_factory, app.state.lessons.storage, app.state.publishing_providers
    )
    github = PublicGithub(app.state.research_providers.fetcher)
    app.state.contributions = ContributionRuntime(app.state.session_factory, github)
    study = study_runtimes(
        app.state.session_factory,
        app.state.launcher,
        program=app.state.program,
        memory=app.state.memory,
    )
    app.state.quiz = study.quiz
    app.state.study = study.study
    app.state.replan = study.replan
    app.state.capture = study.capture
    app.state.career = career_runtimes(
        app.state.session_factory,
        app.state.launcher,
        research=app.state.research,
        memory=app.state.memory,
        publishing=app.state.publishing_providers,
        portfolio_origin=lambda: app.state.settings.portfolio_public_origin,
    )
    app.state.daily = daily_runtimes(
        app.state.session_factory,
        app.state.launcher,
        research=app.state.research,
        career=app.state.career,
        study=study,
        github=github,
    )
    compose_phase10(app)  # IDE (sandbox, professor port) and MCP server (phase 10)
    return study


async def _open_agents(app: FastAPI, stack: AsyncExitStack) -> None:
    """Agent engine (bus, runner, checkpointer) on the feature ports, then the launcher of sessions
    outside the request (D82). Entered after memory and search, so closed before them (the stack
    unwinds in reverse order); resumes interrupted sessions. Finally, the task scheduler (D91)."""
    study = _compose_features(app)
    study.replan.calendar = app.state.calendar
    await start_ide_gateway(app, stack)
    # Injected models (end-to-end flows, tests), otherwise the real factory.
    models: ChatModelSource = app.state.injected_chat_models or app.state.providers.llm_factory
    app.state.runtime = await stack.enter_async_context(
        agent_runtime(
            app.state.settings,
            app.state.session_factory,
            models,
            model_prices(),
            run_settings_source(app.state.session_factory),
            ports=agent_ports(
                app.state.memory,
                app.state.research,
                learning=app.state.learning,
                program=app.state.program,
                lessons=app.state.lessons,
                study=study,
                gap=app.state.career.gap,
                profile=app.state.career.profile,
                cv_templates=app.state.career.cv_templates,
                cv_review=app.state.career.cv_review,
                applications=app.state.career.application_store,
                kit=app.state.career.kit_store,
                interviews=app.state.career.interview_store,
                committee=app.state.career.committee_store,
                radar=app.state.daily.radar_store,
                brief=app.state.daily.brief_store,
                projects=app.state.daily.project_store,
                podcast=app.state.daily.podcast_store,
                ide=app.state.ide_store,
                boss=AgentBossReview(
                    app.state.session_factory, lambda: app.state.providers.sandbox
                ),
            ),
        )
    )
    app.state.launcher.bind(app.state.runtime.runner)
    stack.callback(app.state.launcher.unbind)
    await _open_scheduler(app, stack)


async def _open_scheduler(app: FastAPI, stack: AsyncExitStack) -> None:
    """Scheduled tasks (« J-7 » lessons, D91): after the engine and the linked launcher, so stopped
    before them (a run in progress is cancelled and awaited). `scheduler_enabled = false`
    (tests): none."""
    if app.state.settings.scheduler_enabled:
        context = scheduler_context(
            app.state.session_factory,
            app.state.launcher,
            app.state.lessons,
            app.state.replan,
            app.state.career.applications,
            app.state.daily,
            app.state.book,
        )
        await stack.enter_async_context(open_scheduler(JOBS, context))


def create_app(
    settings: Settings | None = None,
    *,
    memory_providers: MemoryProviders | None = None,
    research_providers: ResearchProviders | None = None,
    publishing_providers: PublishingProviders | None = None,
    chat_models: ChatModelSource | None = None,
) -> FastAPI:
    """Builds the application. `settings` always takes precedence over the `get_settings()` cache;
    `memory_providers` replaces the real composition of Ollama and Qdrant, `research_providers`
    that of SearXNG and Brave, `publishing_providers` that of the PDF rendering of Gotenberg,
    `chat_models` the agents' model factory (tests, end-to-end flows)."""
    settings = settings if settings is not None else get_settings()
    app = FastAPI(
        title="Tremplin",
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        redoc_url=None,
        lifespan=_lifespan,
    )
    app.state.settings = settings
    app.state.injected_memory_providers = memory_providers
    app.state.injected_research_providers = research_providers
    app.state.injected_publishing_providers = publishing_providers
    app.state.injected_chat_models = chat_models
    # Order matters: the last middleware added is the outermost. Errors are
    # registered first so that their 500 goes through CORS (see `UnexpectedErrorMiddleware`).
    register_error_handlers(app)
    # Between error handling and CORS: the 413 goes through CORS (readable by the browser).
    add_body_limits(app, API_PREFIX)
    app.add_middleware(RunSourceHeader)  # choice of the menu « who runs the agents »
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(
        PortfolioPublicHostGuard, origin=lambda: app.state.settings.portfolio_public_origin
    )
    for router in FEATURE_ROUTERS:
        app.include_router(router, prefix=API_PREFIX)
    register_event_schemas(app)
    return app
