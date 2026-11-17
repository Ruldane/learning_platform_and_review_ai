"""README, `.env.example` et `docker-compose.yml` restent d'accord (SPEC 16.2, 17.1) : toute
variable proposée est expliquée, aucun secret n'est livré, Compose passe au back la configuration
de la connexion Google."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
README = (ROOT / "README.md").read_text(encoding="utf-8")
ENV_EXAMPLE = (ROOT / ".env.example").read_text(encoding="utf-8")
COMPOSE = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

# `NOM=valeur`, avec ou sans `#` devant (une variable proposée en commentaire compte aussi).
ASSIGNMENT = re.compile(r"^\s*(?:#\s*)?([A-Z][A-Z0-9_]*)=(.*)$")
SECRET_NAME = re.compile(r"(KEY|SECRET|TOKEN|PASSWORD)")


def env_assignments() -> dict[str, str]:
    found: dict[str, str] = {}
    for line in ENV_EXAMPLE.splitlines():
        match = ASSIGNMENT.match(line)
        if match:
            found[match.group(1)] = match.group(2).strip()
    return found


def test_env_example_is_parsed() -> None:
    names = env_assignments()
    assert {"AUTH_MODE", "ALLOWED_EMAILS", "GOOGLE_CLIENT_ID", "FRONTEND_URL"} <= set(names)
    assert len(names) >= 15


def test_readme_lists_every_env_var_of_env_example() -> None:
    missing = [name for name in env_assignments() if f"`{name}`" not in README]
    assert missing == []


def test_env_example_has_no_value_for_secrets() -> None:
    filled = [
        name for name, value in env_assignments().items() if SECRET_NAME.search(name) and value
    ]
    assert filled == []
    assert env_assignments()["GOOGLE_CLIENT_SECRET"] == ""


def test_env_example_explains_allowed_emails_like_the_readme() -> None:
    for text in (ENV_EXAMPLE, README):
        assert "ALLOWED_EMAILS" in text and "`*`" in text.replace("« * »", "`*`")
    assert "refuse de démarrer" in README and "Requis si AUTH_MODE=google" in ENV_EXAMPLE


def test_compose_passes_the_google_configuration_to_the_backend() -> None:
    backend = COMPOSE[COMPOSE.index("  backend:") : COMPOSE.index("  qdrant:")]
    for name in (
        "AUTH_MODE",
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "ALLOWED_EMAILS",
        "FRONTEND_URL",
        "GOOGLE_REDIRECT_URI",
    ):
        assert re.search(rf"^\s+{name}: \$\{{{name}:-", backend, re.MULTILINE), name
    # Pas de secret en clair dans Compose : les identifiants viennent de `.env`, vides par défaut.
    assert re.search(r"GOOGLE_CLIENT_SECRET: \$\{GOOGLE_CLIENT_SECRET:-\}", backend)
    # `AUTH_MODE` n'est jamais vide : le démarrage serait refusé.
    assert re.search(r"AUTH_MODE: \$\{AUTH_MODE:-local\}", backend)


@pytest.mark.parametrize(
    "needle",
    [
        "docker compose up",
        "http://localhost:5173",
        "http://localhost:8000/api/v1/auth/google/callback",
        "Application Web",
        "écran de consentement",
        "`openid`",
        "alembic upgrade head",
        "SUPPRIMER",
        "Exporter toutes mes données",
        "première qui se connecte prend l'espace local",
        "**jamais** proposée",
        "par `http://localhost:5173`",
        "health/embedding",
    ],
)
def test_readme_covers_the_google_setup_and_data_rights(needle: str) -> None:
    assert needle.lower() in README.lower()


def test_readme_never_contains_a_real_looking_secret() -> None:
    assert not re.search(r"(sk-[A-Za-z0-9]{16,}|GOCSPX-[A-Za-z0-9_-]{10,})", README + ENV_EXAMPLE)
