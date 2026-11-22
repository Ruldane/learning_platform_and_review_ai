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
from app.bootstrap_career import career_runtimes
from app.bootstrap_daily import daily_runtimes
from app.bootstrap_ide import start_ide_gateway
from app.config import Settings, get_settings
from app.core.body_limits import add_body_limits
from app.core.errors import register_error_handlers
from app.core.played import RunSourceHeader
from app.core.providers import MemoryProviders, PublishingProviders, ResearchProviders
from app.db.engine import create_engine, create_session_factory
from app.features.auth.service.authenticator import build_authenticator
from app.features.auth.service.startup import check_google_config
from app.features.book.service.runtime import BookRuntime
from app.features.contributions.service.runtime import ContributionRuntime
from app.features.learning.service.runtime import LearningRuntime
from app.features.program.service.runtime import ProgramRuntime
from app.features.registry import FEATURE_ROUTERS
from app.providers.github.public import PublicGithub
from app.scheduler.registry import JOBS
from app.scheduler.runner import open_scheduler

API_PREFIX = "/api/v1"
_PROBE_TIMEOUT_SECONDS = 3.0


async def _open_external_providers(app: FastAPI, stack: AsyncExitStack) -> MemoryProviders:
    """Fournisseurs de la mémoire, de la recherche web puis des PDF de nos gabarits (D89) : ceux
    qu'on a injectés (tests), sinon la composition réelle, fermée par la pile. La recherche
    reprend le lecteur web de la mémoire. Rend les fournisseurs de la mémoire."""
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
    check_google_config(app.state.settings)  # mode Google mal configuré : refus de démarrer (P11)
    setup_security(app)
    # Le schéma n'est jamais créé ici : en Docker, l'entrypoint lance `alembic upgrade head`.
    # La pile ferme le moteur et le client HTTP même si la composition ou le démarrage échoue.
    async with AsyncExitStack() as stack:
        engine = create_engine(app.state.settings.database_url)
        stack.push_async_callback(engine.dispose)
        app.state.engine = engine
        app.state.session_factory = create_session_factory(engine)
        # Client partagé par les sondes de santé ; le test de la clé Brave a le sien (D74).
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
        if app.state.providers.embedding is not None:  # l'arrêt annule le téléchargement de bge-m3
            stack.push_async_callback(app.state.providers.embedding.aclose)
        # Avant la mémoire : son worker relit la base au démarrage ; un schéma absent doit donner
        # l'indication `alembic upgrade head` plutôt qu'une erreur SQL brute.
        if app.state.settings.auth_mode == "local":
            await ensure_local_user(app)
        app.state.authenticator = build_authenticator(
            app.state.settings, app.state.session_factory, getattr(app.state, "local_user_id", None)
        )
        injected = await _open_external_providers(app, stack)
        # Mémoire : entrée avant le moteur d'agents (qui s'en servira), donc fermée après lui.
        app.state.memory = await stack.enter_async_context(
            open_memory_runtime(app.state.session_factory, injected)
        )
        # Recherche web : après la mémoire (même lecteur web), avant le moteur d'agents.
        app.state.research = await stack.enter_async_context(
            open_research_runtime(
                app.state.session_factory, app.state.research_providers, app.state.providers
            )
        )
        await _open_agents(app, stack)
        yield


def _compose_features(app: FastAPI) -> StudyRuntimes:
    """Runtimes des features que le moteur sert par ses ports : apprentissage, leçons,
    programme, puis l'étude (quiz et révisions, D101 ; sessions guidées, D103). Le lanceur
    existe avant eux (le Conseil le reçoit pour lancer `program_builder`) ; lié au runner
    juste après le moteur."""
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
        app.state.session_factory, app.state.lessons.storage, app.state.lessons.publishing.html_pdf
    )
    app.state.contributions = ContributionRuntime(
        app.state.session_factory, PublicGithub(app.state.research_providers.fetcher)
    )
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
    )
    app.state.daily = daily_runtimes(
        app.state.session_factory,
        app.state.launcher,
        research=app.state.research,
        career=app.state.career,
        study=study,
    )
    compose_phase10(app)  # IDE (bac à sable, port du professeur) et serveur MCP (phase 10)
    return study


async def _open_agents(app: FastAPI, stack: AsyncExitStack) -> None:
    """Moteur d'agents (bus, runner, checkpointer) sur les ports des features, puis lanceur de
    sessions hors requête (D82). Entré après la mémoire et la recherche, donc fermé avant elles
    (la pile dépile à l'envers) ; reprend les sessions interrompues. Enfin, le planificateur des
    tâches (D91)."""
    study = _compose_features(app)
    await start_ide_gateway(app, stack)
    # Modèles injectés (parcours de bout en bout, tests), sinon la fabrique réelle.
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
            ),
        )
    )
    app.state.launcher.bind(app.state.runtime.runner)
    stack.callback(app.state.launcher.unbind)
    await _open_scheduler(app, stack)


async def _open_scheduler(app: FastAPI, stack: AsyncExitStack) -> None:
    """Tâches planifiées (leçons « J-7 », D91) : après le moteur et le lanceur lié, donc arrêtées
    avant eux (passage en cours annulé et attendu). `scheduler_enabled = false` (tests) : aucune."""
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
    """Construit l'application. `settings` prime toujours sur le cache `get_settings()` ;
    `memory_providers` remplace la composition réelle d'Ollama et de Qdrant,
    `research_providers` celle de SearXNG et de Brave, `publishing_providers` celle du rendu
    PDF de Gotenberg, `chat_models` la fabrique des modèles des agents (tests, parcours de bout
    en bout)."""
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
    # Ordre important : le dernier middleware ajouté est le plus externe. Les erreurs sont
    # enregistrées d'abord pour que leur 500 traverse CORS (voir `UnexpectedErrorMiddleware`).
    register_error_handlers(app)
    # Entre la gestion des erreurs et CORS : la 413 traverse CORS (lisible par le navigateur).
    add_body_limits(app, API_PREFIX)
    app.add_middleware(RunSourceHeader)  # choix du menu « qui fait tourner les agents »
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    for router in FEATURE_ROUTERS:
        app.include_router(router, prefix=API_PREFIX)
    register_event_schemas(app)
    return app
