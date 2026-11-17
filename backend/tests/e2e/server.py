"""Serveur du parcours de bout en bout (SPEC 18.2) : l'application réelle (lifespan, moteur,
features, migrations Alembic) sur des fournisseurs factices et des modèles scriptés. Aucun réseau
ni LLM réel.

- Mémoire en local (`HashingEmbedder`, Qdrant en mémoire), web factice (10 pages, fiche d'une
  entreprise fictive, page d'une offre, ressources du brief, onze liens d'offres du radar), rendu
  PDF textuel (`TextHtmlRenderer` : le texte du HTML écrit en un vrai PDF, relisible), polices
  factices, mise en page des PDF locale.
- Modèles scriptés par agent : le Conseil, le CV, l'Assistant de suivi et le brief du matin.
  Le modèle de vision est celui du niveau par défaut (il lit les images).
- Santé sans sonde : tous les services sont annoncés disponibles.

    uv run python -m tests.e2e.server --port 8765 --data-dir <dossier> [--host 0.0.0.0]
    uv run python -m tests.e2e.server --port 8765 --data-dir <dossier> --auth google

`--auth local` (défaut) : l'utilisateur unique, sans connexion. `--auth google` (parcours de
connexion) : le mode Google, avec le faux fournisseur `scripts/fake_oidc.py` monté sous
`/fake-oidc` du même serveur ; `GOOGLE_AUTH_URL`, `GOOGLE_TOKEN_URL`, l'émetteur et l'adresse de
retour pointent dessus (`http://localhost:<port>`, l'application s'ouvre par `localhost`),
`ALLOWED_EMAILS=*`, retour vers l'origine du front (`--origin`). Ouvrir `/api/v1/auth/google/login`
(`?login_hint=<adresse>` choisit le compte) fait un tour de connexion complet, sans mot de passe.

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
from typing import Literal

import uvicorn
from alembic.config import Config
from fastapi import FastAPI

from alembic import command
from app.config import Settings
from app.features.health.router import get_health_service
from app.features.health.service import HealthService
from app.main import create_app
from app.providers.health import HealthStatus
from app.providers.search.fake import FakeSearch
from scripts.fake_oidc import create_fake_oidc_app
from tests.e2e.applications_script import applications_scripts, script_posting_web
from tests.e2e.council_script import DEBATERS, council_scripts, script_web
from tests.e2e.cv_script import cv_scripts, script_company_web
from tests.e2e.daily_script import daily_scripts, script_daily_web
from tests.e2e.scripted_models import Reply, ScriptedModels, merge_scripts
from tests.support.memory import FakeWebReader, fake_memory_providers, fake_publishing_providers
from tests.support.research import fake_research_providers
from tests.support.text_renderer import TextHtmlRenderer

BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_ORIGIN = "http://localhost:5180"
FAKE_OIDC_PATH = "/fake-oidc"
FAKE_CLIENT_ID = "fake-client"

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


def build_app(
    settings: Settings,
    *,
    delays: Mapping[str, float] | None = None,
    scripts: Mapping[str, Sequence[Reply]] | None = None,
) -> FastAPI:
    """L'application sur les fournisseurs factices ; le schéma doit déjà exister. `scripts` : les
    réponses des agents (par défaut celles des parcours n° 1 à n° 4)."""
    memory = fake_memory_providers(settings.data_dir)
    assert isinstance(memory.web, FakeWebReader)
    search = FakeSearch("searxng")
    script_web(memory.web, search)
    script_company_web(memory.web, search)
    script_posting_web(memory.web)
    script_daily_web(memory.web, search)
    app = create_app(
        settings,
        memory_providers=memory,
        research_providers=fake_research_providers(memory.web, searxng=search),
        publishing_providers=fake_publishing_providers(TextHtmlRenderer()),
        chat_models=ScriptedModels(
            scripts
            or merge_scripts(
                daily_scripts(), applications_scripts(), council_scripts(), cv_scripts()
            ),
            delays=delays,
        ),
    )
    app.dependency_overrides[get_health_service] = healthy_service
    if settings.auth_mode == "google":  # le faux fournisseur, sur le même serveur (P5)
        oidc = create_fake_oidc_app(issuer=settings.google_issuer, client_id=FAKE_CLIENT_ID)
        app.mount(FAKE_OIDC_PATH, oidc)
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


def e2e_settings(
    data_dir: Path,
    *,
    origin: str,
    auth: Literal["local", "google"] = "local",
    port: int = 8765,
) -> Settings:
    """Réglages du serveur : base dans `data_dir` même si `DATABASE_URL` est dans
    l'environnement, sans `.env` ni planificateur. `auth="google"` : le mode Google sur le faux
    fournisseur monté sous `/fake-oidc` du serveur (adresses en `http://localhost:<port>`)."""
    common = {
        "data_dir": data_dir,
        "database_url": f"sqlite+aiosqlite:///{(data_dir / DATABASE).as_posix()}",
        "cors_origin": origin,
        "scheduler_enabled": False,
    }
    if auth == "local":
        return Settings(_env_file=None, **common)  # type: ignore[call-arg, arg-type]
    base = f"http://localhost:{port}"
    return Settings(
        _env_file=None,  # type: ignore[call-arg]  # option de pydantic-settings
        auth_mode="google",
        google_client_id=FAKE_CLIENT_ID,
        google_client_secret="fake-secret-for-e2e-only",
        allowed_emails="*",
        google_auth_url=f"{base}{FAKE_OIDC_PATH}/authorize",
        google_token_url=f"{base}{FAKE_OIDC_PATH}/token",
        google_issuer=f"{base}{FAKE_OIDC_PATH}",
        google_redirect_uri=f"{base}/api/v1/auth/google/callback",
        frontend_url=origin,
        **common,  # type: ignore[arg-type]
    )


def _parse(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Serveur des parcours de bout en bout (mode local ou connexion Google factice)."
    )
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--data-dir", type=Path, required=True, help="temporaire ou dédié")
    parser.add_argument("--origin", default=DEFAULT_ORIGIN, help="origine du front (CORS)")
    parser.add_argument(
        "--auth",
        choices=("local", "google"),
        default="local",
        help="local : sans connexion ; google : connexion par le faux fournisseur (/fake-oidc)",
    )
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
    settings = e2e_settings(data_dir, origin=args.origin, auth=args.auth, port=args.port)
    migrate(settings)
    app = build_app(settings, delays=dict.fromkeys(DEBATERS, args.turn_delay))
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
