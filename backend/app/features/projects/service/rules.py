"""Pure mini-project rules (P1 to P3): form of the submission, start of a module's week (the
verdict is that of the engine: `app.agents.tools.project_schema.verdict`). Nothing here imports
the database or another feature."""

from datetime import date
from urllib.parse import urlsplit

DESCRIPTION_MAX = 4000
REPO_URL_MAX = 2048
SCREENSHOTS_MAX = 5
SCREENSHOT_BYTES = 5 * 1024 * 1024
IMAGE_TYPES = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}


def _is_http_link(url: str) -> bool:
    """An http(s) link with a host name, without spaces, of 2,048 characters at most."""
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
    """The fields of a submission to correct (never their value: a 422 does not repeat them).
    Neither link nor description (empty or blank): `repo_url` and `description`; a link that is not
    http(s) or is over 2,048 characters: `repo_url`; a description over 4,000 characters:
    `description`; more than 5 screenshots: `screenshots`. Empty list: the submission is
    acceptable."""
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
    """True if the week starting on Monday `week_start` started on the local day `today`."""
    return today >= week_start
