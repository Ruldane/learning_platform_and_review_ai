"""Loading the prompts: one Markdown file per agent (`prompts/<agent>.md`), rendered with
Jinja2 in strict mode (a missing variable is an error, not an empty string)."""

import re
from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

PROMPTS_DIR = Path(__file__).parent

_AGENT_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
_START = '<<<UNTRUSTED_CONTENT source="{label}">>>'
_END = "<<<END_UNTRUSTED_CONTENT>>>"
# Opening marker (with or without attribute) or closing one, tolerating spaces and case. The
# former French names (`CONTENU_NON_FIABLE`, `FIN_CONTENU_NON_FIABLE`) are still neutralised:
# content stored before the switch to English may carry them.
_MARKER = re.compile(
    r"<<<\s*(?:FIN_|END_)?(?:CONTENU_NON_FIABLE|UNTRUSTED_CONTENT)\b[^>]*>>>", re.IGNORECASE
)
_LABEL_FORBIDDEN = re.compile(r'[\r\n"<>]')


@lru_cache(maxsize=4)
def _environment(directory: Path) -> Environment:
    return Environment(
        loader=FileSystemLoader(directory),
        undefined=StrictUndefined,
        autoescape=False,  # text for a model, not HTML
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_prompt(agent: str, **variables: object) -> str:
    """Renders `prompts/<agent>.md`. `UndefinedError` if a variable is missing, `TemplateNotFound`
    if the file does not exist, `ValueError` if the name is not an agent slug."""
    if not _AGENT_NAME.fullmatch(agent):
        raise ValueError(f"Invalid agent name: {agent!r}")
    return _environment(PROMPTS_DIR).get_template(f"{agent}.md").render(**variables)


def _strip_markers(text: str) -> str:
    # Loop: removing a marker can rebuild another one ("<<<END_<<<END_...>>>...").
    while (stripped := _MARKER.sub("", text)) != text:
        text = stripped
    return text


def untrusted(text: str, label: str) -> str:
    """Frames untrusted content (web page, document): the prompt asks not to follow any
    instruction in it (`_shared/untrusted.md`). Every occurrence of the markers is removed
    from the text, so that it cannot close the framing itself."""
    safe_label = _LABEL_FORBIDDEN.sub("", _strip_markers(label))
    return f"{_START.format(label=safe_label)}\n{_strip_markers(text)}\n{_END}"
