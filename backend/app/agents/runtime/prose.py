"""Texte libre d'une sortie structurée : trop long, il est raccourci au lieu d'être refusé.

Un modèle ne compte pas les caractères : GLM 5.3 dépasse le plafond d'un résumé ou d'une raison
dans la plupart des réponses, et le nouvel essai ne le raccourcit que d'un dixième (D97). Le
refus perdait alors une page notée, voire le Conseil entier. Le plafond reste dans le schéma JSON
envoyé au modèle ; seul le texte qui le dépasse est coupé, en fin de phrase si possible.

Usage : `summary: Prose = Field(min_length=1, max_length=400)` ; dans une liste,
`Annotated[str, Field(max_length=300), ShortenToMax()]` (le plafond avant la métadonnée).
Réservé au texte qu'on lit (résumé, raison, intention) : un identifiant, un nom ou du code
coupé serait faux, il reste refusé.
"""

import logging
import re
from typing import Annotated, Any

from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema

logger = logging.getLogger(__name__)

ELLIPSIS = "…"
_SENTENCE_END = re.compile(r"[.!?…](?=\s)")
_KEEP_SENTENCE = 0.6  # couper en fin de phrase si l'on garde au moins 60 % du plafond
_TRAILING = " \t\n,;:-–—"


def shorten(text: str, limit: int) -> str:
    """`text` ramené à `limit` caractères au plus : à la dernière fin de phrase si elle garde
    l'essentiel, sinon entre deux mots, suivi de « … »."""
    if len(text) <= limit:
        return text
    ends = [m.end() for m in _SENTENCE_END.finditer(text[: limit + 1])]
    if ends and ends[-1] >= limit * _KEEP_SENTENCE:
        return text[: ends[-1]]
    cut = text[: limit - 1]
    if not text[limit - 1].isspace():
        space = cut.rfind(" ")
        if space >= limit // 2:
            cut = cut[:space]
    return cut.rstrip(_TRAILING) + ELLIPSIS


class ShortenToMax:
    """Métadonnée pydantic : lit le plafond (`max_length`) du schéma qu'elle enveloppe et
    raccourcit le texte avant la validation. Sans plafond : `TypeError` dès la définition."""

    def __get_pydantic_core_schema__(
        self, source: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        inner = handler(source)
        limit = inner.get("max_length") if inner["type"] == "str" else None
        if not isinstance(limit, int):
            raise TypeError("Prose demande une chaîne avec un plafond : Field(max_length=...)")

        def fit(value: Any, info: core_schema.ValidationInfo) -> Any:
            if not isinstance(value, str) or len(value) <= limit:
                return value
            logger.info(
                "Texte raccourci : champ %s, %d caractères, plafond %d",
                info.field_name or "(inconnu)",
                len(value),
                limit,
            )
            return shorten(value, limit)

        return core_schema.with_info_before_validator_function(fit, inner)


Prose = Annotated[str, ShortenToMax()]
