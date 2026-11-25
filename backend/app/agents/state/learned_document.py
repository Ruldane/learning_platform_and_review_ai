"""State of the `learned_document` graph: a document marked "already learned" becomes skills."""

from typing import Any, TypedDict


class LearnedDocumentState(TypedDict, total=False):
    document_id: str
    title: str  # document title, reused in the reason of each write
    text: str  # first fragments of the document, joined
    known: str  # skills already in memory (`SkillsSummary.as_text`)
    concepts: list[dict[str, Any]]  # `Concept.model_dump()`, in model order
    created: int  # skills written
    already_known: int  # skills already in memory (nothing written)
    summary: str
