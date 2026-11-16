"""Règles pures des mini projets (P1 à P3) : forme du rendu, début de la semaine d'un module (le
verdict est celui du moteur : `app.agents.tools.project_schema.verdict`). Rien ici n'importe la
base ni une autre feature."""

from datetime import date
from urllib.parse import urlsplit

DESCRIPTION_MAX = 4000
REPO_URL_MAX = 2048
SCREENSHOTS_MAX = 5
SCREENSHOT_BYTES = 5 * 1024 * 1024
IMAGE_TYPES = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}


def _is_http_link(url: str) -> bool:
    """Un lien http(s) avec un nom d'hôte, sans espace, de 2 048 caractères au plus."""
    if len(url) > REPO_URL_MAX or any(ch.isspace() for ch in url):
        return False
    try:
        parts = urlsplit(url)
        host = parts.hostname
    except ValueError:
        return False
    return parts.scheme in ("http", "https") and bool(host)


def submission_problems(
    repo_url: str | None, description: str | None, screenshots: int
) -> list[str]:
    """Les champs d'un rendu à corriger (jamais leur valeur : un 422 ne les répète pas). Ni lien ni
    description (vides ou blancs) : `repo_url` et `description` ; un lien qui n'est pas http(s) ou
    de plus de 2 048 caractères : `repo_url` ; une description de plus de 4 000 caractères :
    `description` ; plus de 5 captures : `screenshots`. Liste vide : le rendu est recevable."""
    link = (repo_url or "").strip()
    text = (description or "").strip()
    problems: list[str] = []
    if not link and not text:
        problems += ["repo_url", "description"]
    else:
        if link and not _is_http_link(link):
            problems.append("repo_url")
        if len(text) > DESCRIPTION_MAX:
            problems.append("description")
    if screenshots > SCREENSHOTS_MAX:
        problems.append("screenshots")
    return problems


def week_started(week_start: date, today: date) -> bool:
    """Vrai si la semaine qui commence le lundi `week_start` a commencé au jour local `today`."""
    return today >= week_start
