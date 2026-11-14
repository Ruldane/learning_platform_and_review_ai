"""Règles pures du Maquettiste (D125) : contenu de démonstration recopié tel quel, question
`cv_template` et analyse de la réponse de January. Aucun port, aucun modèle.

Une ligne du contenu « figure » dans le CV si son texte se retrouve dans le texte visible du PDF
après normalisation de la seule **forme** : Unicode NFKC (ligatures), casse, espaces et retours à
la ligne (une ligne coupée dans le PDF), tirets et apostrophes typographiques. Aucun mot ne peut
changer : le modèle recopie, il n'écrit pas."""

import re
import unicodedata
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from app.agents.tools.cv_schema import CvContent, CvEntry, CvLine, CvSection

MAX_ADJUSTMENTS = 5  # consignes de January, hors des passes automatiques
MAX_INSTRUCTION_CHARS = 500
MAX_INVENTED_SHOWN = 20  # lignes citées au modèle quand il les recopie mal

_SPACES = re.compile(r"\s+")
_DASHES = str.maketrans({"–": "-", "—": "-", "‐": "-", "‑": "-", "’": "'", "‘": "'"})


def plain(text: str) -> str:
    """Forme normalisée d'un texte (voir l'en-tête) : seule la forme change, jamais un mot."""
    text = unicodedata.normalize("NFKC", text).translate(_DASHES).casefold()
    return _SPACES.sub(" ", text).strip()


def _entry_texts(entry: CvEntry) -> list[str]:
    texts = [entry.heading, entry.subheading or "", entry.dates or ""]
    return texts + [line.text for line in entry.lines]


def sample_texts(content: CvContent) -> list[str]:
    """Chaque texte du contenu : nom, accroche, contacts, titres, entrées, lignes."""
    texts = [content.name, content.headline or "", *content.contact]
    for section in content.sections:
        texts.append(section.title)
        for entry in section.entries:
            texts += _entry_texts(entry)
        texts += [item.text for item in section.items]
    return [text for text in texts if text.strip()]


def invented_lines(content: CvContent, original_text: str) -> list[str]:
    """Les textes du contenu absents du texte visible du CV (sans doublon, dans l'ordre)."""
    hay = plain(original_text)
    return list(dict.fromkeys(t for t in sample_texts(content) if plain(t) not in hay))


def _lines(lines: list[CvLine], invented: set[str]) -> list[CvLine]:
    return [CvLine(text=line.text) for line in lines if line.text not in invented]


def _entry(entry: CvEntry, invented: set[str]) -> CvEntry | None:
    kept = CvEntry(
        heading="" if entry.heading in invented else entry.heading,
        subheading=None if entry.subheading in invented else entry.subheading,
        dates=None if entry.dates in invented else entry.dates,
        lines=_lines(entry.lines, invented),
    )
    return kept if kept.heading or kept.subheading or kept.dates or kept.lines else None


def _section(section: CvSection, invented: set[str]) -> CvSection | None:
    """Une section au titre inventé est retirée avec son contenu (un titre est obligatoire)."""
    if section.title in invented:
        return None
    entries = [e for e in (_entry(entry, invented) for entry in section.entries) if e]
    items = _lines(section.items, invented)
    if not entries and not items:
        return None
    return CvSection(key=section.key, title=section.title, entries=entries, items=items)


def verbatim(content: CvContent, invented: list[str]) -> CvContent:
    """Le contenu sans les textes `invented`, sections et entrées vidées retirées ; les
    `fact_ids` sont effacés (une démonstration ne s'adosse à aucun fait du profil)."""
    out = set(invented)
    sections = [s for s in (_section(section, out) for section in content.sections) if s]
    return CvContent(
        name="" if content.name in out else content.name,
        headline=None if content.headline in out else content.headline,
        contact=[item for item in content.contact if item not in out],
        sections=sections,
    )


def copy_retry(invented: list[str]) -> str:
    shown = "\n".join(f"- {text}" for text in invented[:MAX_INVENTED_SHOWN])
    return (
        "Ces textes ne figurent pas tels quels dans le CV :\n"
        f"{shown}\n"
        "Recopie chaque texte mot pour mot depuis le CV (sans puce ni tiret de début de ligne), "
        "ou retire-le. Rends le contenu complet."
    )


def spec_retry(problems: list[str]) -> str:
    listed = "\n".join(f"- {problem}" for problem in problems)
    return (
        f"Ta description a ces défauts :\n{listed}\nCorrige-les et rends la description complète."
    )


# --- Question `cv_template` (preflight G9) -------------------------------------------------------

_VALIDATE = {"value": "validate", "label": "Valider"}
_ADJUST = {"value": "adjust", "label": "Ajuster"}
_RESTART = {"value": "restart", "label": "Recommencer la capture"}
_INSTRUCTION = {
    "id": "instruction",
    "label": "Ce qu'il faut changer",
    "max_length": MAX_INSTRUCTION_CHARS,
}


def question(score: int, adjustments: int) -> dict[str, Any]:
    """La question posée après les passes, quel que soit le score ; au 5e ajustement, seules
    « Valider » et « Recommencer la capture » restent."""
    text = f"Le modèle ressemble à ton CV à {score} %. Tu valides ?"
    if adjustments >= MAX_ADJUSTMENTS:
        return {
            "kind": "cv_template",
            "question": f"{text} Tu as fait les {MAX_ADJUSTMENTS} ajustements possibles.",
            "options": [_VALIDATE, _RESTART],
            "fields": [],
        }
    return {
        "kind": "cv_template",
        "question": text,
        "options": [_VALIDATE, _ADJUST, _RESTART],
        "fields": [_INSTRUCTION],
    }


class DesignAnswer(BaseModel):
    action: Literal["validate", "adjust", "restart"]
    instruction: str = Field(default="", max_length=MAX_INSTRUCTION_CHARS)


def _as_action(value: dict[str, Any]) -> dict[str, Any] | None:
    if "action" in value:
        return value
    answers = value.get("answers")
    if not isinstance(answers, dict) or not isinstance(answers.get("instruction"), str):
        return None
    return {"action": "adjust", "instruction": answers["instruction"]}


def parse_answer(value: Any, adjustments: int) -> DesignAnswer | None:
    """`"validate"`, `"restart"`, `{"answers": {"instruction": …}}` ou `{"action": …,
    "instruction": …}`. La consigne est coupée à 500 caractères plutôt que refusée. `None` (la
    question est reposée) : forme inconnue, ajustement sans consigne, ou au-delà du 5e."""
    if value in ("validate", "restart"):
        return DesignAnswer(action=value)
    if not isinstance(value, dict) or (data := _as_action(value)) is None:
        return None
    if isinstance(data.get("instruction"), str):
        data = {**data, "instruction": data["instruction"].strip()[:MAX_INSTRUCTION_CHARS]}
    try:
        answer = DesignAnswer.model_validate(data)
    except ValidationError:
        return None
    if answer.action != "adjust":
        return DesignAnswer(action=answer.action)
    if not answer.instruction or adjustments >= MAX_ADJUSTMENTS:
        return None
    return answer
