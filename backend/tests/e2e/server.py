"""Serveur du parcours de bout en bout (SPEC 18.2) : l'application réelle (lifespan, moteur,
features, migrations Alembic) sur des fournisseurs factices et les modèles scriptés du Conseil.
Aucun réseau ni LLM réel : mémoire en local (`HashingEmbedder`, Qdrant en mémoire), web factice
de 10 pages, rendu PDF factice (un vrai petit PDF), modèles scriptés par agent, santé sans
sonde (tous les services annoncés disponibles).

    uv run python -m tests.e2e.server --port 8765 --data-dir <dossier> [--host 0.0.0.0]

Le dossier de données doit être temporaire (sous le dossier temporaire du système) ou dédié
(marqueur `.tremplin-e2e`), sans base existante : le serveur y crée sa base et la peuple, il ne
doit jamais toucher des données réelles. La base est toujours `<dossier>/app.db`, quelle que
soit la variable `DATABASE_URL` de l'environnement.

Le planificateur est coupé : la validation du programme lance déjà la chaîne des leçons des
semaines 1 et 2, et un passage planifié pourrait relancer une leçon hors du script."""

import argparse
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path

import uvicorn
from alembic.config import Config
from fastapi import FastAPI

from alembic import command
from app.config import Settings
from app.core.providers import PublishingProviders
from app.features.health.router import get_health_service
from app.features.health.service import HealthService
from app.main import create_app
from app.providers.health import HealthStatus
from app.providers.search.fake import FakeSearch
from scripts.sample_pdf import make_pdf
from tests.e2e.council_script import DEBATERS, council_scripts, script_web
from tests.e2e.scripted_models import ScriptedModels
from tests.support.memory import FakeHtmlRenderer, FakeWebReader, fake_memory_providers
from tests.support.research import fake_research_providers

BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_ORIGIN = "http://localhost:5180"
PDF_LINES = ["Tremplin", "Document de test du parcours de bout en bout."]

HEALTH_CHECKS = ("db", "qdrant", "ollama", "searxng", "gotenberg", "llm")
MARKER = ".tremplin-e2e"
DATABASE = "app.db"


class UnsafeDataDir(Exception):
    """Dossier de données refusé : il pourrait contenir des données réelles."""


class _Faked:
    """Contrôle de santé d'un service remplacé par un faux : toujours disponible, sans sonde."""

    def __init__(self, name: str) -> None:
        self.name = name

    async def check(self) -> HealthStatus:
        return HealthStatus(ok=True, detail="Remplacé par un faux (bout en bout)")


def healthy_service() -> HealthService:
    """Santé du serveur de bout en bout : aucun service réel n'est sondé (aucun réseau)."""
    return HealthService([_Faked(name) for name in HEALTH_CHECKS])


def build_app(settings: Settings, *, delays: Mapping[str, float] | None = None) -> FastAPI:
    """L'application sur les fournisseurs factices ; le schéma doit déjà exister."""
    memory = fake_memory_providers(settings.data_dir)
    assert isinstance(memory.web, FakeWebReader)
    search = FakeSearch("searxng")
    script_web(memory.web, search)
    app = create_app(
        settings,
        memory_providers=memory,
        research_providers=fake_research_providers(memory.web, searxng=search),
        publishing_providers=PublishingProviders(
            html_pdf=FakeHtmlRenderer(pdf=make_pdf(PDF_LINES))
        ),
        chat_models=ScriptedModels(council_scripts(), delays=delays),
    )
    app.dependency_overrides[get_health_service] = healthy_service
    return app


def migrate(settings: Settings) -> None:
    """`alembic upgrade head` sur la base de `settings` (avant la boucle d'uvicorn : `env.py`
    lance la sienne)."""
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(config, "head")


def prepare_data_dir(path: Path, *, temp_root: Path | None = None) -> Path:
    """Le dossier de données du serveur, créé et marqué. Refusé s'il contient déjà une base
    (usage unique), s'il est non vide sans marqueur, ou s'il n'est ni sous le dossier temporaire
    du système (`temp_root`) ni marqué comme dédié au test. Rien n'est créé en cas de refus."""
    data_dir = path.resolve()
    root = (temp_root or Path(tempfile.gettempdir())).resolve()
    marked = (data_dir / MARKER).is_file()
    if (data_dir / DATABASE).exists():
        raise UnsafeDataDir("Dossier de données refusé : il contient déjà une base.")
    if data_dir.is_dir() and any(data_dir.iterdir()) and not marked:
        raise UnsafeDataDir(f"Dossier de données refusé : non vide et sans marqueur {MARKER}.")
    if not marked and not data_dir.is_relative_to(root):
        raise UnsafeDataDir(
            f"Dossier de données refusé : ni temporaire ni dédié (marqueur {MARKER})."
        )
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / MARKER).touch()
    return data_dir


def e2e_settings(data_dir: Path, *, origin: str) -> Settings:
    """Réglages du serveur : base dans `data_dir` même si `DATABASE_URL` est dans
    l'environnement, sans `.env` ni planificateur."""
    return Settings(
        _env_file=None,  # type: ignore[call-arg]  # option de pydantic-settings
        data_dir=data_dir,
        database_url=f"sqlite+aiosqlite:///{(data_dir / DATABASE).as_posix()}",
        cors_origin=origin,
        scheduler_enabled=False,
    )


def _parse(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serveur du parcours de bout en bout n° 1.")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--data-dir", type=Path, required=True, help="temporaire ou dédié")
    parser.add_argument("--origin", default=DEFAULT_ORIGIN, help="origine du front (CORS)")
    parser.add_argument(
        "--turn-delay", type=float, default=1.5, help="secondes avant chaque prise de parole"
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse(argv)
    try:
        data_dir = prepare_data_dir(args.data_dir)
    except UnsafeDataDir as refused:
        sys.exit(str(refused))
    settings = e2e_settings(data_dir, origin=args.origin)
    migrate(settings)
    app = build_app(settings, delays=dict.fromkeys(DEBATERS, args.turn_delay))
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
