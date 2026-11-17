"""Ce que le code impose à la note du professeur (10.A3), quoi que dise le modèle : le type de note
permis par le plan, jamais de texte de remplacement ni de long bloc de code en mode guide, la
démarche seule (jamais de code) au niveau 3 d'un indice, une proposition qui tient dans le fichier
montré, avec l'empreinte de ce fichier. Une règle violée est corrigée par le code, sans nouvel appel
(chaque appel coûte)."""

import re

from app.agents.nodes.professor.context import TeacherContext
from app.agents.nodes.professor.plan import MAX_LEVEL, Plan
from app.agents.tools.ide_port import TeachInputs
from app.agents.tools.ide_schema import TeacherNote

MAX_CODE_LINES = 3  # mode guide : un bloc de code plus long est retiré
REMOVED = "(code retiré : décris la démarche avec tes mots.)"
_FENCE = re.compile(r"```[^\n]*\n(.*?)(?:```|\Z)", re.DOTALL)
_INDENTED = re.compile(r"(?:^(?: {4}|\t)\S.*\n?){4,}", re.MULTILINE)  # plus de MAX_CODE_LINES


def strip_code(text: str, *, keep_short: bool) -> str:
    """Retire les blocs de code (balisés par trois accents graves, ou indentés de 4 lignes et plus)
    de plus de `MAX_CODE_LINES` lignes ; `keep_short=False` retire tous les blocs balisés."""

    def fenced(match: re.Match[str]) -> str:
        code = [line for line in match[1].splitlines() if line.strip()]
        return match[0] if keep_short and len(code) <= MAX_CODE_LINES else REMOVED

    return _INDENTED.sub(REMOVED + "\n", _FENCE.sub(fenced, text)).strip()


def _place(raw: TeacherNote, ctx: TeacherContext) -> tuple[str | None, int | None, int | None]:
    """L'endroit visé s'il est dans le fichier montré (jamais un autre fichier), sinon rien."""
    if raw.path != ctx.path or raw.start_line is None:
        return None, None, None
    start = raw.start_line
    end = raw.end_line if raw.end_line is not None else start
    if not 1 <= start <= end <= ctx.line_count:
        return None, None, None
    return ctx.path, start, end


def finish(
    raw: TeacherNote, plan: Plan, inputs: TeachInputs, ctx: TeacherContext, level: int
) -> tuple[TeacherNote, str | None]:
    """`(note, empreinte)` : la note corrigée selon le plan et le style, et l'empreinte du fichier
    montré si c'est une proposition (sinon `None`)."""
    kind = raw.kind if raw.kind in plan.kinds else plan.kind
    path, start, end = _place(raw, ctx)
    replacement = raw.replacement
    if kind == "proposal" and (path is None or start is None or replacement is None):
        kind = "explanation"  # pas de plage valable dans le fichier montré : une explication
    if kind != "proposal" or inputs.style == "guide":
        replacement = None
    if kind == "annotation" and path is None:
        path, start, end = ctx.path, ctx.focus, ctx.focus  # une annotation vit dans la marge
    text = raw.text
    if kind == "hint" and level >= MAX_LEVEL:
        text = strip_code(text, keep_short=False)  # niveau 3 : la démarche, jamais le code
    elif inputs.style == "guide":
        text = strip_code(text, keep_short=True)
    note = TeacherNote(
        kind=kind,
        level=min(level, MAX_LEVEL) if kind == "hint" else None,
        path=path,
        start_line=start,
        end_line=end,
        text=text or REMOVED,
        replacement=replacement,
    )
    return note, ctx.base_hash if kind == "proposal" else None
