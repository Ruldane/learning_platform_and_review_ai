"""Cleaning, chunking and hashing of memory text (pure functions, no database)."""

import hashlib
import re
import unicodedata
from dataclasses import dataclass

from app.db.models.memory import MemoryKind

CHUNK_TOKENS = 500
CHUNK_OVERLAP = 60
# Token approximation: one word or one punctuation mark (D64). No bge-m3 tokenizer as a
# dependency; the gap with the real count has no impact on search quality.
TOKEN_RE = re.compile(r"\w+|[^\w\s]")

DEFAULT_DOCUMENT_NAME = "Untitled document"
DISPLAY_NAME_MAX = 200

_NO_BREAK_SPACES = {ord(c): " " for c in "   "}
_PATH_SEPARATORS = re.compile(r"[/\\]")
_SPACES = re.compile(r"\s+")
_BLANK_LINES = re.compile(r"\n{3,}")


@dataclass(frozen=True)
class ChunkDraft:
    """A chunk before it is stored."""

    ordinal: int
    text: str
    token_count: int


def _drop_controls(text: str, keep: str = "") -> str:
    return "".join(c for c in text if c in keep or unicodedata.category(c) != "Cc")


def clean_text(text: str) -> str:
    """NFC, `\\n` for every line break, non-breaking spaces → space, control characters removed
    (except `\\n` and `\\t`), trailing spaces removed, at most one blank line."""
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
    """Windows of `size` tokens, advanced by `size - overlap`; stops when the window reaches
    the end. A chunk's text is the slice of the original text from the start of its first
    token to the end of its last (line breaks kept)."""
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError("size must be positive and overlap between 0 and size - 1")
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


def content_hash(kind: MemoryKind, title: str, text: str, *, document_id: str | None = None) -> str:
    """Anti-duplicate hash of an item: a skill is recognised by its title, the other kinds by
    their text; case and spaces do not count."""
    basis = title if kind == "acquis" else text
    normalized = _SPACES.sub(" ", basis.casefold()).strip()
    scope = kind if document_id is None else f"{kind}:{document_id}"
    return hashlib.sha256(f"{scope}\n{normalized}".encode()).hexdigest()


def source_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# Invisible categories removed from a displayed name: controls (Cc), formats (Cf: bidirectional
# overrides and isolates U+202A-202E and U+2066-2069, zero-width spaces), line (Zl) and
# paragraph (Zp) separators. "invoice<U+202E>fdp.exe" can no longer pass itself off as
# "invoiceexe.pdf".
_HIDDEN_CATEGORIES = frozenset({"Cc", "Cf", "Zl", "Zp"})


def _visible(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    return "".join(c for c in text if unicodedata.category(c) not in _HIDDEN_CATEGORIES)


def clean_display(text: str | None) -> str:
    """Text displayed on one line (document name, title entered or received from a site): NFC,
    invisible characters removed (Cc, Cf, Zl, Zp), spaces collapsed, 200 characters at most.
    May return an empty string."""
    return " ".join(_visible(text or "").split())[:DISPLAY_NAME_MAX].strip()


def display_name(raw: str | None) -> str:
    """Display name of a document: last segment of a path (`/` or `\`), cleaned by
    `clean_display`. Never used as a path."""
    segments = [clean_display(s) for s in _PATH_SEPARATORS.split(_visible(raw or ""))]
    return next((s for s in reversed(segments) if s), "") or DEFAULT_DOCUMENT_NAME
