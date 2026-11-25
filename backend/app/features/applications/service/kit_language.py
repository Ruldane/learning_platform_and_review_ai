"""L'analyse de l'offre d'une fiche pour le kit (D143) : celle de l'offre liée si elle est lisible ;
sinon, pour une fiche qui ne garde que la copie figée du texte (saisie à la main), une analyse
minimale (entreprise, intitulé et langue de la fiche : aucune exigence ni mot clé inventés)."""

from typing import Any

from pydantic import ValidationError

from app.agents.tools.posting_schema import PostingAnalysis
from app.db.models.applications import Application

# Mots courants : celui des deux jeux qui revient le plus donne la langue de l'offre.
_ENGLISH = frozenset({"the", "and", "with", "you", "your", "our", "we", "will", "for", "are"})
_FRENCH = frozenset({"le", "la", "les", "des", "et", "vous", "nous", "avec", "pour", "une"})


def text_language(text: str) -> str:
    """`en` ou `fr` (défaut) d'après les mots courants du texte."""
    words = [word.strip(".,;:!?()\"'").casefold() for word in text.split()]
    english = sum(word in _ENGLISH for word in words)
    french = sum(word in _FRENCH for word in words)
    return "en" if english > french else "fr"


def posting_analysis(stored: dict[str, Any] | None, row: Application, text: str) -> PostingAnalysis:
    """L'analyse rangée de l'offre, sinon l'analyse minimale de la fiche."""
    if stored:
        try:
            return PostingAnalysis.model_validate(stored)
        except ValidationError:
            pass  # une analyse illisible : la copie figée de la fiche reste la source
    return PostingAnalysis(
        is_job_posting=True,
        title=row.title.ljust(2, "."),
        company=row.company,
        level="unknown",
        language=text_language(text),
    )
