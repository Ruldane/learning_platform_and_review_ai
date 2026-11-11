"""Texte exact que reçoit un agent d'une recherche en mémoire (outil `memory_search`, banc
d'essai de l'écran Mémoire). Tout ce qui vient d'un document ou d'une écriture est un contenu non
fiable (17.4) : le titre (ramené sur une ligne) et le texte d'un fragment sont encadrés ensemble
par `untrusted`, qui retire les marqueurs qu'ils porteraient. Hors de l'encadrement ne restent
que le type, l'auteur (`user` ou un nom d'agent) et le score. La requête, écrite par l'agent ou
par January, est ramenée sur une ligne et privée de toute suite de trois `<` ou `>`."""

import re
from collections.abc import Sequence

from app.agents.prompts.loader import untrusted
from app.features.memory.schemas import SearchHitOut

_ANGLE_RUNS = re.compile(r"<{3,}|>{3,}")


def _one_line(text: str) -> str:
    return " ".join(text.split())


def _inline(text: str) -> str:
    """Une seule ligne, sans suite de trois `<` ou `>` (boucle : retirer une suite peut en
    rapprocher deux autres)."""
    text = _one_line(text)
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
            f"[{number}] {hit.kind} · auteur {_inline(hit.created_by)} · score {hit.score:.2f}"
        )
        framed = f"Titre : {_one_line(hit.title)}\n{hit.text}"
        lines.append(untrusted(framed, f"memoire:{hit.kind}"))
    return "\n".join(lines)
