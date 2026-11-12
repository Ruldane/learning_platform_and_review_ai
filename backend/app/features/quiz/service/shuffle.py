"""Ordre des questions et des choix (F27, D101). Un nouvel essai garde le même quiz, mais ses
questions et les choix de ses QCM sont mélangés : l'ordre dépend du quiz et du numéro de l'essai
(le nombre de tentatives déjà notées), il est donc le même à la lecture et à l'envoi. Le premier
essai garde l'ordre écrit par l'Examinateur. Déterministe (sha256), sans état."""

import hashlib
from collections.abc import Sequence


def _rank(*parts: object) -> str:
    return hashlib.sha256(":".join(map(str, parts)).encode()).hexdigest()


def question_order(quiz_id: str, round_: int, question_ids: Sequence[str]) -> list[str]:
    """Les ids des questions dans l'ordre affiché à l'essai `round_` (0 : ordre d'origine)."""
    if round_ == 0:
        return list(question_ids)
    return sorted(question_ids, key=lambda qid: _rank(quiz_id, round_, qid))


def choice_order(quiz_id: str, round_: int, question_id: str, count: int) -> list[int]:
    """`affiché → indice d'origine` des choix d'un QCM à l'essai `round_`."""
    if round_ == 0:
        return list(range(count))
    return sorted(range(count), key=lambda i: _rank(quiz_id, round_, question_id, i))
