"""Nettoyage, découpage et empreintes du texte de la mémoire (fonctions pures, sans base)."""

import hashlib
import re
import unicodedata
from dataclasses import dataclass

from app.db.models.memory import MemoryKind

CHUNK_TOKENS = 500
CHUNK_OVERLAP = 60
# Approximation des tokens : un mot ou un signe de ponctuation (D64). Pas de tokenizer bge-m3
# en dépendance ; l'écart avec le vrai décompte est sans conséquence sur la qualité de la recherche.
TOKEN_RE = re.compile(r"\w+|[^\w\s]")

DEFAULT_DOCUMENT_NAME = "Document sans nom"
DISPLAY_NAME_MAX = 200

_NO_BREAK_SPACES = {ord(c): " " for c in "   "}
_PATH_SEPARATORS = re.compile(r"[/\\]")
_SPACES = re.compile(r"\s+")
_BLANK_LINES = re.compile(r"\n{3,}")


@dataclass(frozen=True)
class ChunkDraft:
    """Un fragment avant son enregistrement."""

    ordinal: int
    text: str
    token_count: int


def _drop_controls(text: str, keep: str = "") -> str:
    return "".join(c for c in text if c in keep or unicodedata.category(c) != "Cc")


def clean_text(text: str) -> str:
    """NFC, `\\n` pour tout saut de ligne, espaces insécables → espace, caractères de contrôle
    retirés (sauf `\\n` et `\\t`), espaces de fin de ligne retirés, au plus une ligne vide."""
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n").translate(_NO_BREAK_SPACES)
    text = _drop_controls(text, keep="\n\t")
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    return _BLANK_LINES.sub("\n\n", text).strip()


def count_tokens(text: str) -> int:
    return sum(1 for _ in TOKEN_RE.finditer(text))


def chunk_text(
    text: str, *, size: int = CHUNK_TOKENS, overlap: int = CHUNK_OVERLAP
) -> list[ChunkDraft]:
    """Fenêtres de `size` tokens, avancées de `size - overlap` ; on s'arrête quand la fenêtre
    atteint la fin. Le texte d'un fragment est la tranche du texte d'origine qui va du début
    de son premier token à la fin de son dernier (retours à la ligne conservés)."""
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError("size doit être positif et overlap compris entre 0 et size - 1")
    tokens = list(TOKEN_RE.finditer(text))
    chunks: list[ChunkDraft] = []
    start = 0
    while start < len(tokens):
        end = min(start + size, len(tokens))
        piece = text[tokens[start].start() : tokens[end - 1].end()]
        chunks.append(ChunkDraft(len(chunks), piece, end - start))
        if end == len(tokens):
            break
        start += size - overlap
    return chunks


def content_hash(kind: MemoryKind, title: str, text: str) -> str:
    """Empreinte anti doublon d'un élément : un acquis se reconnaît à son titre, les autres
    types à leur texte ; casse et espaces ne comptent pas."""
    basis = title if kind == "acquis" else text
    normalized = _SPACES.sub(" ", basis.casefold()).strip()
    return hashlib.sha256(f"{kind}\n{normalized}".encode()).hexdigest()


def source_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# Catégories invisibles retirées d'un nom affiché : contrôles (Cc), formats (Cf : forçages et
# isolats bidirectionnels U+202A-202E et U+2066-2069, espaces de largeur nulle), séparateurs de
# ligne (Zl) et de paragraphe (Zp). « facture<U+202E>fdp.exe » ne peut plus se faire passer pour
# « factureexe.pdf ».
_HIDDEN_CATEGORIES = frozenset({"Cc", "Cf", "Zl", "Zp"})


def _visible(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    return "".join(c for c in text if unicodedata.category(c) not in _HIDDEN_CATEGORIES)


def clean_display(text: str | None) -> str:
    """Texte affiché sur une ligne (nom de document, titre saisi ou reçu d'un site) : NFC,
    caractères invisibles retirés (Cc, Cf, Zl, Zp), espaces regroupés, 200 caractères au plus.
    Peut rendre une chaîne vide."""
    return " ".join(_visible(text or "").split())[:DISPLAY_NAME_MAX].strip()


def display_name(raw: str | None) -> str:
    """Nom d'affichage d'un document : dernier segment d'un chemin (`/` ou `\`), nettoyé par
    `clean_display`. Jamais utilisé comme chemin."""
    segments = [clean_display(s) for s in _PATH_SEPARATORS.split(_visible(raw or ""))]
    return next((s for s in reversed(segments) if s), "") or DEFAULT_DOCUMENT_NAME
