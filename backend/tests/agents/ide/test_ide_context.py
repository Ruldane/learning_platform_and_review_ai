"""Le contexte du professeur (10.A3) est borné par le code : un seul fichier, ±30 lignes, 40 lignes
d'erreur et 2 000 caractères au plus, 4 échanges ; les règles de note ; le niveau de modèle."""

import pytest

from app.agents.nodes.professor.context import (
    ERROR_CHARS,
    ERROR_LINES,
    EXCHANGES,
    THREAD_CHARS,
    WINDOW_LINES,
    build_context,
    file_hash,
)
from app.agents.nodes.professor.plan import plan_of
from app.agents.nodes.professor.rules import REMOVED, strip_code
from app.agents.tools.ide_port import NoteView, RunView, TeachInputs

BIG = "\n".join(f"ligne_{n} = {n}" for n in range(1, 401)) + "\n"
OTHER_FILE = "secret_autre_fichier = 1\n"


def note(number: int) -> NoteView:
    return NoteView(
        id=f"n{number}",
        kind="reference" if number == 9 else "hint",
        author="professor",
        level=1,
        file_path=None,
        line_start=None,
        text=f"échange numéro {number} " + "mot " * 400,
        error_key=None,
    )


def inputs(output: str = "", style: str = "guide") -> TeachInputs:
    run = RunView("r1", "run", "done", 1, output, None) if output else None
    return TeachInputs(
        title="Exercice",
        statement="Énoncé",
        files={"main.py": BIG, "autre.py": OTHER_FILE},
        entry="main.py",
        passed=False,
        style="pair" if style == "pair" else "guide",
        run=run,
        notes=[note(n) for n in range(1, 21)],
    )


def test_context_is_bounded() -> None:
    long_output = "\n".join(f"sortie {n} " + "x" * 80 for n in range(300))
    ctx = build_context(inputs(long_output), file_path="main.py", cursor_line=200)
    window_lines = ctx.window.splitlines()
    assert len(window_lines) == 2 * WINDOW_LINES + 1
    assert ctx.first_line == 170 and ctx.last_line == 230 and ctx.line_count == 400
    assert window_lines[0].endswith("ligne_170 = 170") and window_lines[-1].endswith(
        "ligne_230 = 230"
    )
    assert len(ctx.error_tail) <= ERROR_CHARS and len(ctx.error_tail.splitlines()) <= ERROR_LINES
    assert ctx.error_tail.endswith("x" * 80)  # c'est la fin de la sortie qui est gardée
    # Les 12 derniers messages, hors renvois, et le fil entier borné en caractères.
    assert 0 < len(ctx.exchanges) <= EXCHANGES
    assert sum(len(line) for line in ctx.exchanges) <= THREAD_CHARS
    assert "échange numéro 20" in ctx.exchanges[-1] and "numéro 9 " not in " ".join(ctx.exchanges)
    assert all(len(line) < 500 for line in ctx.exchanges)
    assert OTHER_FILE.strip() not in ctx.window  # jamais un second fichier
    assert ctx.base_hash == file_hash(BIG)


def test_window_is_clamped_at_the_file_edges() -> None:
    top = build_context(inputs(), file_path="main.py", cursor_line=1)
    bottom = build_context(inputs(), file_path="main.py", cursor_line=9_999)
    assert (top.first_line, top.last_line) == (1, 31)
    assert (bottom.first_line, bottom.last_line) == (370, 400) and bottom.focus == 400


def test_focus_follows_the_error_then_the_entry() -> None:
    trace = 'Traceback (most recent call last):\n  File "/work/a1/main.py", line 77, in <module>\n'
    ctx = build_context(inputs(trace + "ValueError: x"))
    assert (ctx.path, ctx.focus) == ("main.py", 77)
    plain = build_context(inputs())
    assert (plain.path, plain.focus) == ("main.py", 1)
    unknown = build_context(inputs(), file_path="inconnu.py", cursor_line=5)
    assert unknown.path == "main.py"  # un fichier qui n'existe pas est ignoré


@pytest.mark.parametrize(
    ("trigger", "style", "tier", "kinds"),
    [
        ("hint", "guide", "rapide", ("hint",)),
        ("hint", "pair", "rapide", ("hint",)),
        ("run_error", "guide", "rapide", ("hint",)),
        ("run_error", "pair", "rapide", ("annotation",)),
        ("idle", "pair", "rapide", ("annotation",)),
        ("question", "guide", "fort", ("explanation",)),
        ("question", "pair", "fort", ("explanation", "proposal")),
    ],
)
def test_plan_tier_follows_the_kind_of_note(
    trigger: str, style: str, tier: str, kinds: tuple[str, ...]
) -> None:
    plan = plan_of(trigger, style)  # type: ignore[arg-type]
    assert (plan.tier, plan.kinds) == (tier, kinds)


def test_run_ok_never_plans_a_call() -> None:
    with pytest.raises(ValueError):
        plan_of("run_ok", "guide")


def test_strip_code_keeps_short_blocks_and_removes_long_ones() -> None:
    short = "Voici :\n```python\na = 1\nb = 2\nc = 3\n```\nfin"
    long = "Voici :\n```python\na\nb\nc\nd\n```\nfin"
    assert strip_code(short, keep_short=True) == short
    assert REMOVED in strip_code(long, keep_short=True) and "d\n" not in strip_code(
        long, keep_short=True
    )
    assert REMOVED in strip_code(short, keep_short=False)
    indented = "Texte\n    a = 1\n    b = 2\n    c = 3\n    d = 4\nfin"
    assert REMOVED in strip_code(indented, keep_short=True)
    unclosed = "Début\n```python\n" + "\n".join(f"l{n}" for n in range(10))
    assert "l9" not in strip_code(unclosed, keep_short=True)


def test_guide_style_drops_replacement_even_if_a_plan_allowed_a_proposal() -> None:
    """Défense en profondeur : en mode guide, `finish` ne laisse jamais passer un remplacement."""
    from app.agents.nodes.professor.plan import Plan
    from app.agents.nodes.professor.rules import finish
    from app.agents.tools.ide_schema import TeacherNote

    guide = inputs(style="guide")
    ctx = build_context(guide, file_path="main.py", cursor_line=5)
    raw = TeacherNote(
        kind="proposal", path="main.py", start_line=5, text="Voici.", replacement="x = 1"
    )
    note, base_hash = finish(raw, Plan(("proposal",), "fort"), guide, ctx, 1)
    assert note.replacement is None and note.kind == "proposal" and base_hash == ctx.base_hash
    pair = inputs(style="pair")
    note, _ = finish(
        raw,
        Plan(("proposal",), "fort"),
        pair,
        build_context(pair, file_path="main.py", cursor_line=5),
        1,
    )
    assert note.replacement == "x = 1" and (note.start_line, note.end_line) == (5, 5)
