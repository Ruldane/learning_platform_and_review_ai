"""HTML templates of the PDFs (lesson, program; SPEC 3.5, 17.4, D89): Jinja with automatic escaping
everywhere (`.j2` included), and an unknown variable is an error. The only HTML inserted as is,
is the body of a lesson, already cleaned by `nh3` (`lessons.service.markdown`)."""

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
    """`name` relative to the templates folder, for example `lesson/lesson.html.j2`."""
    return _ENV.get_template(name).render(**context)
