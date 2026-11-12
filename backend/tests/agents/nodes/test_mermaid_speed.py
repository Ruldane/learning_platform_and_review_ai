"""Temps d'analyse du Mermaid du Scribe (D85 §11f, round 4) : l'analyse est synchrone dans la
boucle d'événements, elle doit rester linéaire. Re-relecture 3 : `A -- ` suivi de 3000 espaces
prenait 28 s. Chaque entrée pathologique, à la taille maximale admise, passe en moins de 50 ms."""

import re
import time
from collections.abc import Callable, Iterator
from types import ModuleType

import pytest

from app.agents.nodes import mermaid_edges, mermaid_grammar, mermaid_tree
from app.agents.nodes.mermaid_grammar import MAX_LINE_CHARS
from app.agents.nodes.mermaid_rules import MAX_CODE_CHARS, mermaid_problems

BUDGET_S = 0.05
BOARD_MAX = 6000  # `BoardDraft.mermaid`
HEADER = "flowchart TD\n"


def _elapsed(call: Callable[[], object]) -> float:
    """Meilleur de trois mesures : un ramasse-miettes ou un poste chargé ne fait pas échouer ;
    un retour arrière, lui, se répète à chaque mesure."""
    times = []
    for _ in range(3):
        start = time.perf_counter()
        call()
        times.append(time.perf_counter() - start)
    return min(times)


def _filled(prefix: str, filler: str, tail: str, size: int) -> str:
    return prefix + filler * ((size - len(prefix) - len(tail)) // len(filler)) + tail


def _one_line(prefix: str, filler: str, tail: str = "x") -> str:
    return HEADER + _filled(prefix, filler, tail, MAX_LINE_CHARS)


def _many_lines(prefix: str, filler: str, tail: str = "x") -> str:
    line = _filled(prefix, filler, tail, MAX_LINE_CHARS)
    return HEADER + "\n".join([line] * ((BOARD_MAX - len(HEADER)) // (len(line) + 1)))


OPENERS = ["A -- ", "A -. ", "A == ", "A --", "A -.", "A ==", 'A["', "A[", "A -->|", "A <"]
FILLERS = [" ", "-", ".", "=", "\t", "a ", "- ", ". ", "= ", "-.", "#1", "<br", "&", ";", '"']


@pytest.mark.parametrize("opener", OPENERS)
@pytest.mark.parametrize("filler", FILLERS)
def test_pathological_boards_are_analysed_in_linear_time(opener: str, filler: str) -> None:
    for code in (
        _one_line(opener, filler),
        _many_lines(opener, filler),
        HEADER + _filled(opener, filler, "x", BOARD_MAX - len(HEADER)),  # ligne trop longue
    ):
        assert _elapsed(lambda code=code: mermaid_problems(code)) < BUDGET_S


def test_oversized_code_is_refused_before_any_analysis() -> None:
    code = HEADER + "A -- " + " " * MAX_CODE_CHARS + "x"
    assert _elapsed(lambda: mermaid_problems(code)) < BUDGET_S
    assert mermaid_problems(code) == [f"schéma de plus de {MAX_CODE_CHARS} caractères"]


def _patterns(module: ModuleType) -> Iterator[re.Pattern[str]]:
    for value in vars(module).values():
        if isinstance(value, re.Pattern):
            yield value
        elif isinstance(value, dict):
            yield from (v for v in value.values() if isinstance(v, re.Pattern))


PATTERNS = [p for m in (mermaid_grammar, mermaid_edges, mermaid_tree) for p in _patterns(m)]
PATHOLOGICAL = [c * 5000 + tail for c in [" ", "-", ".", "=", "#", "|", "\t", "1"] for tail in "x;"]


def test_every_regex_is_found_by_the_speed_test() -> None:
    assert len(PATTERNS) >= 10


@pytest.mark.parametrize("pattern", PATTERNS, ids=lambda p: p.pattern[:30])
def test_no_regex_backtracks_on_repeated_characters(pattern: re.Pattern[str]) -> None:
    for text in PATHOLOGICAL:
        for start in (0, 1):
            elapsed = _elapsed(lambda text=text, start=start: list(pattern.finditer(text, start)))
            assert elapsed < BUDGET_S, (pattern.pattern, text[:3])
            assert _elapsed(lambda text=text: pattern.fullmatch(text)) < BUDGET_S
