"""Chargement des prompts : un fichier Markdown par agent (`prompts/<agent>.md`), rendu avec
Jinja2 en mode strict (une variable absente est une erreur, pas une chaîne vide)."""

import re
from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

PROMPTS_DIR = Path(__file__).parent

_AGENT_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
_START = '<<<CONTENU_NON_FIABLE source="{label}">>>'
_END = "<<<FIN_CONTENU_NON_FIABLE>>>"
# Marqueur ouvrant (avec ou sans attribut) ou fermant, en tolérant espaces et casse.
_MARKER = re.compile(r"<<<\s*(?:FIN_)?CONTENU_NON_FIABLE\b[^>]*>>>", re.IGNORECASE)
_LABEL_FORBIDDEN = re.compile(r'[\r\n"<>]')


@lru_cache(maxsize=4)
def _environment(directory: Path) -> Environment:
    return Environment(
        loader=FileSystemLoader(directory),
        undefined=StrictUndefined,
        autoescape=False,  # du texte pour un modèle, pas du HTML
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_prompt(agent: str, **variables: object) -> str:
    """Rend `prompts/<agent>.md`. `UndefinedError` si une variable manque, `TemplateNotFound`
    si le fichier n'existe pas, `ValueError` si le nom n'est pas un slug d'agent."""
    if not _AGENT_NAME.fullmatch(agent):
        raise ValueError(f"Nom d'agent invalide : {agent!r}")
    return _environment(PROMPTS_DIR).get_template(f"{agent}.md").render(**variables)


def _strip_markers(text: str) -> str:
    # Boucle : retirer un marqueur peut en reconstituer un autre (« <<<FIN_<<<FIN_…>>>… »).
    while (stripped := _MARKER.sub("", text)) != text:
        text = stripped
    return text


def untrusted(text: str, label: str) -> str:
    """Encadre un contenu non fiable (page web, document) : le prompt demande de n'y suivre
    aucune instruction (`_shared/untrusted.md`). Toute occurrence des marqueurs est retirée
    du texte, pour qu'il ne puisse pas refermer lui-même l'encadrement."""
    safe_label = _LABEL_FORBIDDEN.sub("", _strip_markers(label))
    return f"{_START.format(label=safe_label)}\n{_strip_markers(text)}\n{_END}"
