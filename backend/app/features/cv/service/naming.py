"""Nom du fichier d'un CV produit (D118) : ASCII, lisible, jamais vide. Il contient le nom de
January : jamais journalisé."""

import re
import unicodedata

MAX_PART = 40
_NOT_KEPT = re.compile(r"[^A-Za-z0-9-]")


def _part(text: str | None) -> str:
    """Une partie du nom : accents retirés, mots joints par « _ », caractères hors
    `[A-Za-z0-9-]` retirés, 40 caractères au plus (sans « _ » ni « - » final)."""
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text)
    plain = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    words = [_NOT_KEPT.sub("", word) for word in plain.split()]
    joined = "_".join(word for word in words if word)
    return joined[:MAX_PART].rstrip("_-")


def cv_filename(name: str, company: str | None, title: str | None) -> str:
    """« CV_<Nom>_<Entreprise>_<Poste>.pdf » ; une partie vide est omise, « CV.pdf » au pire."""
    parts = [part for part in (_part(name), _part(company), _part(title)) if part]
    return "_".join(["CV", *parts]) + ".pdf"
