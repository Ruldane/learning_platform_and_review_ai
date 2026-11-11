"""Texte exact que reçoit un agent d'une recherche en mémoire (outil `memory_search`, banc
d'essai de l'écran Mémoire). Tout fragment est un contenu non fiable (17.4) : il est encadré par
`untrusted`, qui retire les marqueurs que le texte porterait. Les titres et la requête, qui
peuvent venir d'un document, sont ramenés sur une ligne et privés de tout `<<<` ou `>>>`."""

import re
from collections.abc import Sequence

from app.agents.prompts.loader import untrusted
from app.features.memory.schemas import SearchHitOut

_ANGLE_RUNS = re.compile(r"<{3,}|>{3,}")


def _inline(text: str) -> str:
    """Une seule ligne, sans suite de trois `<` ou `>` (boucle : retirer une suite peut en
    rapprocher deux autres)."""
    text = " ".join(text.split())
    while (stripped := _ANGLE_RUNS.sub("", text)) != text:
        text = stripped
    return text


def format_for_agent(query: str, hits: Sequence[SearchHitOut]) -> str:
    shown = _inline(query)
    if not hits:
        return f"Mémoire — aucun fragment pour « {shown} »."
    lines = [f"Mémoire — {len(hits)} fragment(s) pour « {shown} » :"]
    for number, hit in enumerate(hits, start=1):
        lines.append(
            f"[{number}] {hit.kind} · {_inline(hit.title)} · "
            f"auteur {_inline(hit.created_by)} · score {hit.score:.2f}"
        )
        lines.append(untrusted(hit.text, f"memoire:{hit.kind}"))
    return "\n".join(lines)
