"""Fichiers figés joints aux PDF (D89) : feuilles de style, pied de page, `mermaid.min.js` et
`render.js`. Ce sont les seuls scripts qui s'exécutent dans le Chromium de Gotenberg ; Mermaid
est téléchargé une fois (`https://cdn.jsdelivr.net/npm/mermaid@<version>/dist/mermaid.min.js`,
même version que la dépendance du front) et son empreinte est vérifiée avant tout envoi."""

import hashlib
import re
from functools import cache

from app.templates import TEMPLATES_DIR

MERMAID_VERSION = "12.3.0"
MERMAID_SHA256 = "336df803d87a38b70a01e736e666c8f7601d2ce42f5e47c8fafe5d721074b9a3"

_ASSETS_DIR = TEMPLATES_DIR / "assets"
# Un nom simple (aucun séparateur de chemin) ou `dossier/nom` sous les gabarits.
_NAME = re.compile(r"[a-z0-9][a-z0-9_.-]{0,63}")
_PATH = re.compile(r"(lesson|program)/[a-z0-9][a-z0-9_.-]{0,63}")


@cache
def asset(name: str) -> bytes:
    """Contenu d'un fichier de `templates/assets/` (lu une fois). `mermaid.min.js` est refusé
    si son empreinte n'est pas `MERMAID_SHA256` (`RuntimeError`)."""
    if not _NAME.fullmatch(name) or ".." in name:
        raise ValueError("nom de ressource refusé")
    data = (_ASSETS_DIR / name).read_bytes()
    if name == "mermaid.min.js" and hashlib.sha256(data).hexdigest() != MERMAID_SHA256:
        raise RuntimeError("mermaid.min.js ne correspond pas à l'empreinte figée")
    return data


@cache
def template_file(path: str) -> str:
    """Fichier statique d'un gabarit (`lesson/lesson.css`, `lesson/footer.html`…), en UTF-8."""
    if not _PATH.fullmatch(path) or ".." in path:
        raise ValueError("chemin de gabarit refusé")
    return (TEMPLATES_DIR / path).read_text(encoding="utf-8")
