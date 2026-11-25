"""What the code imposes on the professor's note (10.A3), whatever the model says: the note type
allowed by the plan, never replacement text or a long code block in guide mode, only the approach
(never code) at hint level 3, a proposal that fits in the file shown, with that file's
fingerprint. A violated rule is corrected by the code, without a new call (each call costs)."""

import re

from app.agents.nodes.professor.context import TeacherContext
from app.agents.nodes.professor.plan import MAX_LEVEL, Plan
from app.agents.tools.ide_port import TeachInputs
from app.agents.tools.ide_schema import TeacherNote

MAX_CODE_LINES = 3  # guide mode: a longer code block is removed
REMOVED = "(Code removed. Describe the approach in your own words.)"
_FENCE = re.compile(r"```[^\n]*\n(.*?)(?:```|\Z)", re.DOTALL)
_INDENTED = re.compile(r"(?:^(?: {4}|\t)\S.*\n?){4,}", re.MULTILINE)  # more than MAX_CODE_LINES


def strip_code(text: str, *, keep_short: bool) -> str:
    """Removes the code blocks (fenced by three backticks, or indented by 4 lines or more) of
    more than `MAX_CODE_LINES` lines; `keep_short=False` removes all the fenced blocks."""

    def fenced(match: re.Match[str]) -> str:
        code = [line for line in match[1].splitlines() if line.strip()]
        return match[0] if keep_short and len(code) <= MAX_CODE_LINES else REMOVED

    return _INDENTED.sub(REMOVED + "\n", _FENCE.sub(fenced, text)).strip()


def _place(raw: TeacherNote, ctx: TeacherContext) -> tuple[str | None, int | None, int | None]:
    """The targeted place if it is in the file shown (never another file), otherwise nothing."""
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
    """`(note, fingerprint)`: the note corrected according to the plan and the style, and the
    fingerprint of the file shown if it is a proposal (otherwise `None`)."""
    kind = raw.kind if raw.kind in plan.kinds else plan.kind
    path, start, end = _place(raw, ctx)
    replacement = raw.replacement
    if kind == "proposal" and (path is None or start is None or replacement is None):
        kind = "explanation"  # no valid range in the file shown: an explanation
    if kind != "proposal" or inputs.style == "guide":
        replacement = None
    if kind == "annotation" and path is None:
        path, start, end = ctx.path, ctx.focus, ctx.focus  # an annotation lives in the margin
    text = raw.text
    if kind == "hint" and level >= MAX_LEVEL:
        text = strip_code(text, keep_short=False)  # level 3: the approach, never the code
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
