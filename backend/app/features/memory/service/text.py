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


def display_name(raw: str | None) -> str:
    """Nom d'affichage d'un document : dernier segment d'un chemin (`/` ou `\\`), sans
    caractère de contrôle. Jamais utilisé comme chemin."""
    cleaned = unicodedata.normalize("NFC", _drop_controls(raw or ""))
    segments = [s.strip() for s in _PATH_SEPARATORS.split(cleaned)]
    name = next((s for s in reversed(segments) if s), "")
    return name[:DISPLAY_NAME_MAX] or DEFAULT_DOCUMENT_NAME
