"""Gabarits HTML des PDF (leçon, programme ; SPEC 3.5, 17.4, D89) : Jinja avec échappement
automatique partout (`.j2` compris), variable inconnue = erreur. Le seul HTML inséré tel quel est
le corps d'une leçon, déjà nettoyé par `nh3` (`lessons.service.markdown`)."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

TEMPLATES_DIR = Path(__file__).parent

_ENV = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=True,
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
    auto_reload=False,
)


def render_template(name: str, **context: object) -> str:
    """`name` relatif au dossier des gabarits, par exemple `lesson/lesson.html.j2`."""
    return _ENV.get_template(name).render(**context)
