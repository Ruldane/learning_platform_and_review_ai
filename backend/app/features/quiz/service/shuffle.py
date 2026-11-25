"""Order of questions and choices (F27, D101). A new attempt keeps the same quiz, but its
questions and the choices of its multiple-choice questions are shuffled: the order depends on
the quiz and on the attempt number (the number of attempts already graded), so it is the same
when reading and when submitting. The first attempt keeps the order written by the Examiner.
Deterministic (sha256), stateless."""

import hashlib
from collections.abc import Sequence


def _rank(*parts: object) -> str:
    return hashlib.sha256(":".join(map(str, parts)).encode()).hexdigest()


def question_order(quiz_id: str, round_: int, question_ids: Sequence[str]) -> list[str]:
    """The question ids in the order shown at attempt `round_` (0: original order)."""
    if round_ == 0:
        return list(question_ids)
    return sorted(question_ids, key=lambda qid: _rank(quiz_id, round_, qid))


def choice_order(quiz_id: str, round_: int, question_id: str, count: int) -> list[int]:
    """`shown → original index` of the choices of a multiple-choice question at attempt `round_`."""
    if round_ == 0:
        return list(range(count))
    return sorted(range(count), key=lambda i: _rank(quiz_id, round_, question_id, i))
