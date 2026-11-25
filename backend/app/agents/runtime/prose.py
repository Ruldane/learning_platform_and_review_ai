"""Free text of a structured output: too long, it is shortened instead of being refused.

A model does not count characters: GLM 5.3 exceeds the cap of a summary or a reason in most
replies, and the retry only shortens it by a tenth (D97). The refusal then lost a graded page,
even the whole Council. The cap stays in the JSON schema sent to the model; only the text that
exceeds it is cut, at the end of a sentence if possible.

Usage: `summary: Prose = Field(min_length=1, max_length=400)`; in a list,
`Annotated[str, Field(max_length=300), ShortenToMax()]` (the cap before the metadata).
Reserved for text that is read (summary, reason, intent): an identifier, a name or cut code
would be wrong, it stays refused.
"""

import logging
import re
from typing import Annotated, Any

from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema

logger = logging.getLogger(__name__)

ELLIPSIS = "…"
_SENTENCE_END = re.compile(r"[.!?…](?=\s)")
_KEEP_SENTENCE = 0.6  # cut at the end of a sentence if at least 60% of the cap is kept
_TRAILING = " \t\n,;:-–—"


def shorten(text: str, limit: int) -> str:
    """`text` brought down to at most `limit` characters: at the last end of a sentence if it
    keeps the essentials, otherwise between two words, followed by "…"."""
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
    """Pydantic metadata: reads the cap (`max_length`) of the schema it wraps and
    shortens the text before validation. Without a cap: `TypeError` from the definition."""

    def __get_pydantic_core_schema__(
        self, source: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        inner = handler(source)
        limit = inner.get("max_length") if inner["type"] == "str" else None
        if not isinstance(limit, int):
            raise TypeError("Prose needs a string with a cap: Field(max_length=...)")

        def fit(value: Any, info: core_schema.ValidationInfo) -> Any:
            if not isinstance(value, str) or len(value) <= limit:
                return value
            logger.info(
                "Text shortened: field %s, %d characters, cap %d",
                info.field_name or "(unknown)",
                len(value),
                limit,
            )
            return shorten(value, limit)

        return core_schema.with_info_before_validator_function(fit, inner)


Prose = Annotated[str, ShortenToMax()]
