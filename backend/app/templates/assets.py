"""Frozen files attached to the PDFs (D89): stylesheets, footer, `mermaid.min.js` and
`render.js`. These are the only scripts that run in Gotenberg's Chromium; Mermaid
is downloaded once (`https://cdn.jsdelivr.net/npm/mermaid@<version>/dist/mermaid.min.js`,
same version as the front end's dependency) and its fingerprint is checked before any sending."""

import hashlib
import re
from functools import cache

from app.templates import TEMPLATES_DIR

MERMAID_VERSION = "12.3.0"
MERMAID_SHA256 = "336df803d87a38b70a01e736e666c8f7601d2ce42f5e47c8fafe5d721074b9a3"

_ASSETS_DIR = TEMPLATES_DIR / "assets"
# A plain name (no path separator) or `folder/name` under the templates.
_NAME = re.compile(r"[a-z0-9][a-z0-9_.-]{0,63}")
_PATH = re.compile(r"(lesson|program|cv)/[a-z0-9][a-z0-9_.-]{0,63}")


@cache
def asset(name: str) -> bytes:
    """Content of a file of `templates/assets/` (read once). `mermaid.min.js` is refused
    if its fingerprint is not `MERMAID_SHA256` (`RuntimeError`)."""
    if not _NAME.fullmatch(name) or ".." in name:
        raise ValueError("resource name refused")
    data = (_ASSETS_DIR / name).read_bytes()
    if name == "mermaid.min.js" and hashlib.sha256(data).hexdigest() != MERMAID_SHA256:
        raise RuntimeError("mermaid.min.js does not match the frozen fingerprint")
    return data


@cache
def template_file(path: str) -> str:
    """Static file of a template (`lesson/lesson.css`, `lesson/footer.html`...), in UTF-8."""
    if not _PATH.fullmatch(path) or ".." in path:
        raise ValueError("template path refused")
    return (TEMPLATES_DIR / path).read_text(encoding="utf-8")
