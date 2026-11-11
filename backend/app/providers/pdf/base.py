"""Port de l'extraction du texte d'un PDF (fichier importé ou URL lue)."""

from typing import Protocol

from app.core.errors import AppError

MAX_PDF_PAGES = 500
MAX_TEXT_CHARS = 2_000_000


class PdfUnreadable(AppError):
    """PDF chiffré, endommagé ou qui n'est pas un PDF. Ne cite jamais le fichier ni son contenu."""

    def __init__(self) -> None:
        super().__init__(
            "pdf_unreadable",
            "PDF illisible (protégé par mot de passe ou endommagé).",
            status_code=422,
        )


class PdfTextExtractor(Protocol):
    async def extract_text(self, data: bytes) -> str:
        """Texte des `MAX_PDF_PAGES` premières pages, tronqué à `MAX_TEXT_CHARS` caractères."""
        ...
