"""Nom du fichier d'un CV produit (D118) : ASCII, lisible, jamais vide. Il contient le nom de
January : jamais journalisé."""

import re
import unicodedata

MAX_PART = 40
_NOT_KEPT = re.compile(r"[^A-Za-z0-9-]")
# Ligatures et lettres que NFKD ne décompose pas.
_LIGATURES = str.maketrans({"œ": "oe", "Œ": "Oe", "æ": "ae", "Æ": "Ae", "ß": "ss"})


def _part(text: str | None) -> str:
    """Une partie du nom : ligatures développées, accents retirés, mots joints par « _ »,
    caractères hors `[A-Za-z0-9-]` retirés (un mot fait de tirets seulement aussi), 40
    caractères au plus (sans « _ » ni « - » final). Un nom non latin disparaît."""
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text.translate(_LIGATURES))
    plain = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    words = [_NOT_KEPT.sub("", word) for word in plain.split()]
    joined = "_".join(word for word in words if word.strip("-"))
    return joined[:MAX_PART].rstrip("_-")


def cv_filename(name: str, company: str | None, title: str | None) -> str:
    """« CV_<Nom>_<Entreprise>_<Poste>.pdf » ; une partie vide est omise, « CV.pdf » au pire."""
    parts = [part for part in (_part(name), _part(company), _part(title)) if part]
    return "_".join(["CV", *parts]) + ".pdf"


def kit_filename(company: str | None, title: str | None) -> str:
    """« Kit_<Entreprise>_<Poste>.zip » (archive du kit de candidature) ; « Kit.zip » au pire."""
    parts = [part for part in (_part(company), _part(title)) if part]
    return "_".join(["Kit", *parts]) + ".zip"
