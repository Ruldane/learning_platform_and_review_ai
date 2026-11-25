"""The kit pieces as the API sees them (D143): a `kit_items` row becomes a `KitItemOut`, and the
text January edits is re-checked by the code (`text_claims`, as at writing time: SPEC 1,
18.3). Pure functions.

Stored content conventions (D142): `followups` = 7-day email, a `---` line, 14-day email;
`linkedin` = invitation, a `---` line, message; `form_answers` = `### question` then the answer
("For you to fill in" or "To complete" if the code emptied it; the French spellings stored
before the switch to English are still recognised)."""

import re
from dataclasses import dataclass
from typing import cast

from app.agents.nodes.tracker.honesty import allowed_phrases
from app.agents.tools.kit_schema import (
    NO_QUESTION,
    SALARY_BLANK,
    TO_COMPLETE,
    KitContext,
    split_followups,
    split_parts,
)
from app.agents.tools.salary import is_salary_question
from app.agents.tools.text_claims import text_claims
from app.db.models.applications import KitItem
from app.features.applications.schemas_kit import KitItemOut, KitKind, KitSourceOut, KitStatus

CHECKED: frozenset[str] = frozenset({"letter", "linkedin", "followups", "form_answers", "pitch"})
_QUESTION = re.compile(r"^### +(.*)$")
# The French spellings are what rows stored before the switch to English contain.
_SALARY_BLANKS = frozenset({SALARY_BLANK, "À remplir par toi"})
_BLANKS = _SALARY_BLANKS | {TO_COMPLETE, "À compléter"}
_NO_QUESTIONS = frozenset({NO_QUESTION, "Aucune question éliminatoire repérée dans l'offre."})


def pending_item(kind: KitKind) -> KitItemOut:
    """A piece not stored yet."""
    return KitItemOut(
        id=None,
        kind=kind,
        status="pending",
        content="",
        flags=[],
        salary_fields=0,
        words=None,
        error=None,
        sources=[],
        edited=False,
        updated_at=None,
    )


def form_items(content: str) -> list[tuple[str, str]]:
    """`(question, answer)` of a `form_answers` (the text under each `### question`); without a
    title, the whole text is an answer without a question."""
    items: list[tuple[str, list[str]]] = []
    for line in content.splitlines():
        if match := _QUESTION.match(line):
            items.append((match.group(1).strip(), []))
        elif items:
            items[-1][1].append(line)
    if not items:
        text = content.strip()
        return [("", text)] if text and text not in _NO_QUESTIONS else []
    return [(question, "\n".join(lines).strip()) for question, lines in items]


def form_bodies(content: str) -> list[str]:
    return [body for _, body in form_items(content)]


def salary_fields(content: str) -> int:
    """The answers left to January because they commit her salary expectation."""
    return sum(1 for body in form_bodies(content) if body in _SALARY_BLANKS)


def words_of(kind: str, content: str) -> int | dict[str, int] | None:
    """The word count stored in `meta.words` (same shape as at writing time)."""
    if kind in ("letter", "pitch"):
        return len(content.split())
    if kind == "linkedin":
        return len(split_parts(content)[-1].split())
    if kind == "followups":
        day_7, day_14 = split_followups(content)
        return {"day_7": len(day_7.split()), "day_14": len(day_14.split())}
    return None


def total_words(words: object) -> int | None:
    if isinstance(words, bool):
        return None
    if isinstance(words, int):
        return words
    if isinstance(words, dict):
        return sum(value for value in words.values() if isinstance(value, int))
    return None


def sources_of(meta: dict[str, object]) -> list[KitSourceOut]:
    """The dossier pages stored with the piece, in the order of the `[n]` citations."""
    refs = meta.get("source_refs")
    if not isinstance(refs, list):
        return []
    return [
        KitSourceOut(rank=rank, url=str(ref.get("url", "")), title=ref.get("title") or None)
        for rank, ref in enumerate(refs, 1)
        if isinstance(ref, dict)
    ]


def item_out(row: KitItem) -> KitItemOut:
    meta = dict(row.meta or {})
    flags = meta.get("flags")
    error = meta.get("error")
    return KitItemOut(
        id=row.id,
        kind=cast(KitKind, row.kind),  # the column is a text, the values are KitKind
        status=cast(KitStatus, row.status),
        content=row.content,
        flags=[str(flag) for flag in flags] if isinstance(flags, list) else [],
        salary_fields=salary_fields(row.content) if row.kind == "form_answers" else 0,
        words=total_words(meta.get("words")),
        error=str(error) if row.status == "failed" and error else None,
        sources=sources_of(meta) if row.kind == "company_brief" else [],
        edited=row.edited,
        updated_at=row.updated_at,
    )


def texts_to_check(kind: str, content: str) -> list[str]:
    """The texts of January that `text_claims` re-reads: never the form questions."""
    if kind in ("linkedin", "followups"):
        return split_parts(content)
    if kind == "form_answers":
        # The salary expectation is January's: no profile fact states it.
        return [
            body
            for question, body in form_items(content)
            if body not in _BLANKS and not is_salary_question(question)
        ]
    return [content]


def has_blank(kind: str, content: str) -> bool:
    """A form answer is still to be filled in or completed."""
    return kind == "form_answers" and any(body in _BLANKS for body in form_bodies(content))


def flagged(kind: str, content: str, ctx: KitContext) -> list[str]:
    """The terms (figures, tools, titles, names) that the profile does not state, without
    duplicates. For a piece outside `CHECKED`, none: the dossier comes from the web, the CV is
    not a written text."""
    if kind not in CHECKED:
        return []
    allowed = allowed_phrases(ctx)
    terms: list[str] = []
    for text in texts_to_check(kind, content):
        for claim in text_claims(text, ctx.profile, allowed=allowed):
            if claim.term not in terms:
                terms.append(claim.term)
    return terms


@dataclass(frozen=True)
class Rechecked:
    status: KitStatus
    meta: dict[str, object]


def needs_context(status: str, content: str) -> bool:
    """The piece will be re-read: a ready piece with text is not."""
    return not (status == "ready" and content.strip())


def recheck(row: KitItem, content: str, ctx: KitContext | None) -> Rechecked:
    """The status and the `meta` after January's edit. A piece "to check" (or failed, which she
    fills in) is re-read by `text_claims`: `flags` updated, "ready" if nothing remains (no term,
    no answer to fill in); a ready piece stays ready. An empty text is always "to check"."""
    meta = {key: value for key, value in (row.meta or {}).items() if key not in ("error", "code")}
    words = words_of(row.kind, content)
    if words is not None:
        meta["words"] = words
    if not needs_context(row.status, content):
        return Rechecked("ready", meta)
    if ctx is None:
        raise ValueError("The kit context is needed to re-read a piece.")
    terms = flagged(row.kind, content, ctx)
    if terms:
        meta["flags"] = terms
    else:
        meta.pop("flags", None)
    clean = content.strip() and not terms and not has_blank(row.kind, content)
    return Rechecked("ready" if clean else "to_check", meta)
