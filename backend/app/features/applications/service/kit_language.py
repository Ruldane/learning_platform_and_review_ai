"""Analysis of a record's offer for the kit (D143): that of the linked offer if it is readable;
otherwise, for a record that only keeps the frozen copy of the text (typed by hand), a minimal
analysis (company, title and language of the record: no requirement or keyword invented)."""

from typing import Any

from pydantic import ValidationError

from app.agents.tools.posting_schema import PostingAnalysis
from app.db.models.applications import Application

# Common words: whichever of the two sets matches most gives the language of the offer.
_ENGLISH = frozenset({"the", "and", "with", "you", "your", "our", "we", "will", "for", "are"})
_FRENCH = frozenset({"le", "la", "les", "des", "et", "vous", "nous", "avec", "pour", "une"})


def text_language(text: str) -> str:
    """`en` or `fr` (default) based on the common words of the text."""
    words = [word.strip(".,;:!?()\"'").casefold() for word in text.split()]
    english = sum(word in _ENGLISH for word in words)
    french = sum(word in _FRENCH for word in words)
    return "en" if english > french else "fr"


def posting_analysis(stored: dict[str, Any] | None, row: Application, text: str) -> PostingAnalysis:
    """The stored analysis of the offer, otherwise the minimal analysis of the record."""
    if stored:
        try:
            return PostingAnalysis.model_validate(stored)
        except ValidationError:
            pass  # an unreadable analysis: the frozen copy of the record stays the source
    return PostingAnalysis(
        is_job_posting=True,
        title=row.title.ljust(2, "."),
        company=row.company,
        level="unknown",
        language=text_language(text),
    )
