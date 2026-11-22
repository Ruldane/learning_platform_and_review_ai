"""Réponses déterministes du Bibliothécaire avant et après le retrait d'une note."""

import re
from collections.abc import Sequence

from langchain_core.messages import BaseMessage

from tests.e2e.lesson_script import prompt_of
from tests.e2e.scripted_models import Reply

NOTE_CODE = "TX-482-B"


def _with_note(messages: Sequence[BaseMessage]) -> str:
    prompt = prompt_of(messages)
    if NOTE_CODE not in prompt:
        raise RuntimeError("Le document synchronisé manque dans le contexte de recette.")
    prefix = prompt[: prompt.index(NOTE_CODE)]
    cited = re.findall(r"^\[(\d+)\] ", prefix, flags=re.MULTILINE)
    if not cited:
        raise RuntimeError("Référence numérotée absente de la recette du Cerveau.")
    return f"La note indique le code {NOTE_CODE}. [{cited[-1]}]"


def _without_note(messages: Sequence[BaseMessage]) -> str:
    if NOTE_CODE in prompt_of(messages):
        raise RuntimeError("Une note retirée figure encore dans le contexte de recette.")
    return "Je ne retrouve plus la note du calendrier."


def brain_scripts() -> dict[str, list[Reply]]:
    return {"brain_librarian": [_with_note, _without_note]}
